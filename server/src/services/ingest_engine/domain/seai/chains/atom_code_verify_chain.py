from __future__ import annotations

from src.services.ingest_engine.domain.seai.chains.base import SEAIChain
from src.services.ingest_engine.domain.seai.models import Atom, AtomDraft, Episode, SEAIConfig
from src.services.ingest_engine.domain.seai.utils.evidence import annotations, atom_quotes, find_quote_spans


class AtomCodeVerifyChain(SEAIChain):
    def __init__(self, config: SEAIConfig, id_factory):
        super().__init__()
        self.config = config
        self.id_factory = id_factory

    def run(self, raw_text: str, episode: Episode, atom_drafts: list[AtomDraft]) -> list[Atom]:
        atoms = []
        rejected = 0
        for draft in atom_drafts:
            # LLM verifier is helpful, but code owns the final source-bound gate.
            role = str(draft.get("atom_role", "")).strip().lower()
            if role not in {"direct", "relation"}:
                rejected += 1
                continue

            try:
                confidence = float(draft.get("confidence", 0))
            except (TypeError, ValueError):
                rejected += 1
                continue
            if confidence < self.config.min_confidence:
                rejected += 1
                continue

            # Every atom must cite exact text inside this episode, not just nearby raw input.
            quotes = atom_quotes(draft)
            evidence_spans = find_quote_spans(raw_text, quotes, episode["spans"])
            if not evidence_spans or len(evidence_spans) != len(quotes):
                rejected += 1
                continue

            content = str(draft.get("content", "")).strip()
            if not content:
                rejected += 1
                continue
            if _weak_short_atom(content):
                rejected += 1
                continue

            atoms.append({
                "id": self.id_factory.new_id(),
                "raw_input_id": episode["raw_input_id"],
                "episode_id": episode["id"],
                "content": content,
                "atom_role": role,
                "annotations": annotations(draft.get("annotations", [])),
                "confidence": confidence,
                "evidence_spans": evidence_spans,
            })
        if rejected:
            self.logger.warning("seai_atom_code_verify_rejected rejected_count=%s episode_id=%s", rejected, episode.get("id"))
        return atoms

    verified_atoms = run


def _weak_short_atom(content: str) -> bool:
    lowered = content.lower().strip(" .")
    if any(phrase in lowered for phrase in {"simple terms", "dramatic", "special and dangerous", "strongest traits"}):
        return True
    words = [word for word in lowered.replace("'", "").split() if word]
    if len(words) >= 7:
        return False
    # Short atoms are allowed only when they read like concrete facts, not labels.
    concrete_verbs = {
        "is", "are", "was", "were", "has", "have", "had", "likes", "hates", "wants",
        "believes", "sees", "gave", "killed", "joined", "watched", "learns", "refuses",
        "bought", "punched", "apologized", "left",
    }
    return not any(word in concrete_verbs for word in words)
