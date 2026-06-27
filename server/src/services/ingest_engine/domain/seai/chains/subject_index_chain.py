from __future__ import annotations

import json
from typing import Any

from src.services.ingest_engine.domain.seai.chains.base import SEAIChain


class SubjectIndexChain(SEAIChain):
    def __init__(self, client):
        super().__init__()
        self.client = client

    def run(
        self,
        raw_preview: str,
        episodes: list[dict[str, Any]],
        atoms: list[dict[str, Any]],
        candidate_subjects: list[dict[str, Any]],
    ) -> dict[str, Any]:
        del raw_preview
        system = (
            "Create a neutral memory subject index for new source-backed evidence. "
            "Subjects are recurring or central concepts, not every noun. Reuse an existing subject id when it clearly matches. "
            "Subjects and links are retrieval hints only, not factual authority. Preserve uncertainty and avoid hidden motives or global conclusions. "
            "Return compact valid JSON only. No markdown."
        )
        human = (
            "Return JSON with this shape:\n"
            "{"
            '"subjects":[{"ref":"s1","existing_subject_id":null,"name":"subject name","kind":"topic",'
            '"aliases":["alias"],"summary":"short neutral hint"}],'
            '"links":[{"subject_ref":"s1","episode_id":"episode id","atom_id":null,"relation":"mentions",'
            '"confidence":0.8,"reason":"why this evidence belongs","event_time":null,"time_label":null}]'
            "}\n\n"
            "Allowed subject kinds: project, person, place, topic, theme, question, decision, problem, event, story, research, other.\n"
            "Allowed link relations: mentions, problem, decision, event, question, change, plan, evidence, status, other.\n"
            "Rules:\n"
            "- Return at most 6 subjects and 18 links.\n"
            "- If the evidence has any clear central subject, return at least one subject and one link even on first mention.\n"
            "- Use moderate granularity: central or recurring subjects only.\n"
            "- Link only to episode_id and atom_id values provided below.\n"
            "- Prefer episode-level links; use atom_id only when an atom is the best evidence.\n"
            "- event_time is optional and only for clear dates/times from the source.\n"
            "- time_label may preserve the raw time phrase.\n"
            "- Keep summaries and reasons short, neutral, and non-citable.\n\n"
            f"EXISTING_CANDIDATE_SUBJECTS:\n{json.dumps(_candidate_payload(candidate_subjects), ensure_ascii=False)}\n\n"
            f"EPISODES:\n{json.dumps(_episode_payload(episodes), ensure_ascii=False)}\n\n"
            f"ATOMS:\n{json.dumps(_atom_payload(atoms), ensure_ascii=False)}"
        )
        data = self.client.invoke_json(system, human)
        return data if isinstance(data, dict) else {}


def _episode_payload(episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": episode.get("id"),
            "summary": str(episode.get("summary", ""))[:240],
        }
        for episode in episodes[:30]
    ]


def _atom_payload(atoms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": atom.get("id"),
            "episode_id": atom.get("episode_id"),
            "content": str(atom.get("content", ""))[:180],
            "atom_role": atom.get("atom_role"),
            "annotations": (atom.get("annotations") or [])[:4],
        }
        for atom in atoms[:60]
    ]


def _candidate_payload(subjects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": subject.get("id"),
            "name": subject.get("name"),
            "kind": subject.get("kind"),
            "aliases": (subject.get("aliases") or [])[:4],
            "summary": str(subject.get("summary", ""))[:180],
        }
        for subject in subjects[:8]
    ]
