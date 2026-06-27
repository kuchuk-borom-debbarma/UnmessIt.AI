from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

SUBJECT_KINDS = {
    "project", "person", "place", "topic", "theme", "question",
    "decision", "problem", "event", "story", "research", "other",
}
LINK_RELATIONS = {
    "mentions", "problem", "decision", "event", "question",
    "change", "plan", "evidence", "status", "other",
}


class MemorySubjectIndexer:
    def __init__(self, repository, chain, id_factory):
        self.repository = repository
        self.chain = chain
        self.id_factory = id_factory

    def index(self, raw_text: str, episodes: list[dict[str, Any]], atoms: list[dict[str, Any]]) -> dict[str, int]:
        if not episodes:
            return {"subjects": 0, "links": 0}

        terms = _important_terms([
            raw_text[:1200],
            *[episode.get("summary", "") for episode in episodes],
            *[atom.get("content", "") for atom in atoms],
        ])
        candidates = self.repository.find_candidate_subjects(terms, limit=12)
        data = self.chain.run("", episodes, atoms, candidates)
        subjects, links = self._normalize(data, episodes, atoms, candidates)
        self.repository.save_subject_index(subjects, links)
        logger.info("memory_subject_indexed subject_count=%s link_count=%s", len(subjects), len(links))
        return {"subjects": len(subjects), "links": len(links)}

    def _normalize(
        self,
        data: dict[str, Any],
        episodes: list[dict[str, Any]],
        atoms: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        valid_episode_ids = {episode["id"] for episode in episodes}
        atom_by_id = {atom["id"]: atom for atom in atoms}
        candidate_by_id = {subject["id"]: subject for subject in candidates}
        subject_by_ref: dict[str, dict[str, Any]] = {}
        subjects = []

        for draft in _as_list(data.get("subjects"))[:6]:
            ref = str(draft.get("ref") or "").strip()
            name = str(draft.get("name") or "").strip()
            existing_id = str(draft.get("existing_subject_id") or "").strip()
            existing = candidate_by_id.get(existing_id)
            if not ref or (not name and not existing):
                continue

            subject = {
                "id": existing["id"] if existing else self.id_factory.new_id(),
                "name": name or existing["name"],
                "kind": _kind(draft.get("kind"), existing),
                "aliases": _clean_aliases(draft.get("aliases")),
                "summary": str(draft.get("summary") or (existing or {}).get("summary") or "").strip()[:240],
            }
            if existing:
                subject["aliases"] = _merge_aliases(existing.get("aliases", []), subject["aliases"])
            subject_by_ref[ref] = subject
            subjects.append(subject)

        links = []
        seen_links = set()
        for draft in _as_list(data.get("links"))[:18]:
            subject = subject_by_ref.get(str(draft.get("subject_ref") or "").strip())
            episode_id = str(draft.get("episode_id") or "").strip()
            atom_id = str(draft.get("atom_id") or "").strip() or None
            if not subject or episode_id not in valid_episode_ids:
                continue
            if atom_id:
                atom = atom_by_id.get(atom_id)
                if not atom or atom.get("episode_id") != episode_id:
                    continue
            key = (subject["id"], episode_id, atom_id)
            if key in seen_links:
                continue
            seen_links.add(key)
            links.append({
                "id": self.id_factory.new_id(),
                "subject_id": subject["id"],
                "raw_input_id": _raw_input_id(episodes, episode_id),
                "episode_id": episode_id,
                "atom_id": atom_id,
                "relation": _allowed(draft.get("relation"), LINK_RELATIONS),
                "confidence": _confidence(draft.get("confidence")),
                "reason": str(draft.get("reason") or "").strip()[:240],
                "event_time": _optional_str(draft.get("event_time")),
                "time_label": _optional_str(draft.get("time_label")),
            })

        linked_subject_ids = {link["subject_id"] for link in links}
        subjects = [subject for subject in subjects if subject["id"] in linked_subject_ids]
        return subjects, links


def _important_terms(values: list[str]) -> list[str]:
    stop = {"what", "with", "from", "that", "this", "they", "them", "were", "have", "about", "source"}
    result = []
    seen = set()
    for value in values:
        for term in re.findall(r"[A-Za-z][A-Za-z']+", str(value)):
            clean = term.strip("'")
            lowered = clean.lower()
            if len(clean) < 4 or lowered in stop or lowered in seen:
                continue
            seen.add(lowered)
            result.append(clean)
    return result[:12]


def _as_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _allowed(value: Any, allowed: set[str]) -> str:
    clean = str(value or "").strip().lower()
    return clean if clean in allowed else "other"


def _kind(value: Any, existing: dict[str, Any] | None) -> str:
    clean = str(value or "").strip().lower()
    if clean in SUBJECT_KINDS:
        return clean
    if existing and existing.get("kind") in SUBJECT_KINDS:
        return existing["kind"]
    return "other"


def _clean_aliases(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    result = []
    seen = set()
    for alias in value:
        clean = str(alias).strip()
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            result.append(clean[:120])
    return result[:8]


def _merge_aliases(existing: list[str], new: list[str]) -> list[str]:
    return _clean_aliases([*existing, *new])


def _confidence(value: Any) -> float:
    try:
        return min(1.0, max(0.0, float(value)))
    except (TypeError, ValueError):
        return 0.5


def _optional_str(value: Any) -> str | None:
    clean = str(value or "").strip()
    return clean[:120] if clean else None


def _raw_input_id(episodes: list[dict[str, Any]], episode_id: str) -> str:
    for episode in episodes:
        if episode["id"] == episode_id:
            return episode["raw_input_id"]
    return ""
