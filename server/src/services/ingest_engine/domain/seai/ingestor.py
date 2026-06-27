from __future__ import annotations

import logging
from dataclasses import dataclass

from src.services.ingest_engine.domain.seai.chains.base import Chain
from src.services.ingest_engine.domain.seai.models import Atom, Episode, EpisodeDraft, SEAIConfig, SourceWindow
from src.services.ingest_engine.domain.seai.utils.evidence import EvidenceResolver, episode_quotes
from src.services.ingest_engine.ports.inbound.ingestor import Ingestor

logger = logging.getLogger(__name__)


@dataclass
class SEAIChains:
    # The swappable chain slots. The ingest method below defines the order.
    preprocess: Chain
    window: Chain
    split_episodes: Chain
    summarize_episode: Chain
    verify_episode: Chain
    extract_atoms: Chain
    verify_atoms: Chain
    code_verify_atoms: Chain


class SEAIIngestor(Ingestor):
    def __init__(
        self,
        config: SEAIConfig,
        repository,
        vector_indexer,
        chains: SEAIChains,
        id_factory,
        evidence_resolver: EvidenceResolver | None = None,
    ):
        self.config = config
        self.repository = repository
        self.vector_indexer = vector_indexer
        self.chains = chains
        self.id_factory = id_factory
        self.evidence = evidence_resolver or EvidenceResolver()

    def ingest(self, data: str, job_id: str = None):
        job_id = job_id or self.id_factory.new_id()
        data = self._preprocess(data, job_id)
        logger.info("seai_ingest_start job_id=%s raw_chars=%s raw_preview=%r", job_id, len(data), _preview(data))

        # Raw text is saved before any LLM work so spans always point to durable truth.
        raw_input_id = self.repository.save_raw_input(job_id, data)
        logger.info("seai_raw_saved job_id=%s raw_input_id=%s", job_id, raw_input_id)

        # Chain flow: windows -> episode drafts -> verified episodes -> verified atoms.
        episodes, atoms = self._build_index(data, raw_input_id, job_id)
        if not episodes:
            episode, fallback_atoms = self._fallback_episode(data, raw_input_id, job_id)
            episodes.append(episode)
            atoms.extend(fallback_atoms)

        logger.info("seai_save_start job_id=%s episode_count=%s atom_count=%s", job_id, len(episodes), len(atoms))
        self.repository.save_seai(episodes, atoms)
        logger.info("seai_save_complete job_id=%s episode_count=%s atom_count=%s", job_id, len(episodes), len(atoms))

        if self.vector_indexer:
            self.vector_indexer.add(episodes, atoms)
        logger.info("seai_ingest_complete job_id=%s episode_count=%s atom_count=%s", job_id, len(episodes), len(atoms))
        return {"raw_input_id": raw_input_id, "episodes": episodes, "atoms": atoms}

    @property
    def preprocessor(self):
        return self.chains.preprocess

    @preprocessor.setter
    def preprocessor(self, value):
        self.chains.preprocess = value

    def _preprocess(self, text: str, job_id: str) -> str:
        try:
            return self.chains.preprocess.run(text)
        except Exception as exc:
            logger.warning("seai_preprocessor_failed job_id=%s fallback=raw error=%s", job_id, exc)
            return text

    def _build_index(self, raw_text: str, raw_input_id: str, job_id: str) -> tuple[list[Episode], list[Atom]]:
        episodes, atoms = [], []
        # Windowing keeps local models alive and gives each splitter call small context.
        windows = self.chains.window.run(raw_text)
        logger.info("seai_windows_created job_id=%s window_count=%s", job_id, len(windows))

        for window_index, window in enumerate(windows, start=1):
            drafts = self._episode_drafts(window, job_id, window_index)
            logger.info(
                "seai_window_split job_id=%s window_index=%s episode_draft_count=%s window_preview=%r",
                job_id,
                window_index,
                len(drafts),
                _preview(window["text"]),
            )
            for draft in drafts:
                episode = self._episode_from_draft(raw_text, raw_input_id, draft, window)
                if not episode:
                    continue
                episodes.append(episode)
                episode_atoms = self._atoms_for_episode(raw_text, episode, job_id)
                atoms.extend(episode_atoms)
                logger.info(
                    "seai_episode_processed job_id=%s episode_id=%s summary=%r episode_preview=%r atom_count=%s atom_previews=%r",
                    job_id,
                    episode["id"],
                    _preview(episode.get("summary", "")),
                    _preview(episode["text"]),
                    len(episode_atoms),
                    [_preview(atom["content"], 120) for atom in episode_atoms],
                )
        return episodes, atoms

    def _episode_drafts(self, window: SourceWindow, job_id: str, window_index: int) -> list[EpisodeDraft]:
        try:
            drafts = self.chains.split_episodes.run(
                window["text"],
                prev_context=window.get("prev_context", ""),
                next_context=window.get("next_context", ""),
            )
        except Exception as exc:
            logger.warning("seai_splitter_failed job_id=%s window_index=%s fallback=true error=%s", job_id, window_index, exc)
            drafts = []
        if not drafts:
            # Keep ingest useful even when the splitter fails: one window becomes one episode.
            return [{"summary": "", "evidence_quotes": [window["text"]]}]
        return [draft for draft in drafts if episode_quotes(draft)] or [{"summary": "", "evidence_quotes": [window["text"]]}]

    def _episode_from_draft(self, raw_text: str, raw_input_id: str, draft: EpisodeDraft, window: SourceWindow) -> Episode | None:
        spans = self.evidence.episode_spans(raw_text, draft, window)
        if not spans:
            logger.warning("seai_episode_draft_rejected reason=no_spans window_start=%s window_end=%s", window["start_idx"], window["end_idx"])
            return None

        episode_text = self.evidence.episode_text(raw_text, spans)
        fallback = str(draft.get("summary", "")).strip()
        summary = self.chains.summarize_episode.run(episode_text, fallback)
        summary = self.chains.verify_episode.run(episode_text, summary, fallback)
        return {
            "id": self.id_factory.new_id(),
            "raw_input_id": raw_input_id,
            "text": episode_text,
            "summary": summary,
            "spans": spans,
        }

    def _atoms_for_episode(self, raw_text: str, episode: Episode, job_id: str) -> list[Atom]:
        try:
            extracted = self.chains.extract_atoms.run(episode["text"])
        except Exception as exc:
            # Atom extraction is optional; losing atoms should not lose the source episode.
            logger.warning("seai_atom_extract_failed job_id=%s episode_id=%s error=%s", job_id, episode["id"], exc)
            extracted = []
        try:
            verified = self.chains.verify_atoms.run(episode["text"], extracted)
        except Exception as exc:
            logger.warning("seai_atom_verifier_failed job_id=%s episode_id=%s error=%s", job_id, episode["id"], exc)
            verified = extracted
        return self.chains.code_verify_atoms.run(raw_text, episode, verified)

    def _fallback_episode(self, raw_text: str, raw_input_id: str, job_id: str) -> tuple[Episode, list[Atom]]:
        logger.warning("seai_no_episodes_fallback job_id=%s", job_id)
        summary = self.chains.summarize_episode.run(raw_text, "")
        episode = {
            "id": self.id_factory.new_id(),
            "raw_input_id": raw_input_id,
            "text": raw_text,
            "summary": self.chains.verify_episode.run(raw_text, summary, ""),
            "spans": [{"start": 0, "end": len(raw_text)}],
        }
        return episode, self._atoms_for_episode(raw_text, episode, job_id)


def _preview(text: str, limit: int = 240) -> str:
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."
