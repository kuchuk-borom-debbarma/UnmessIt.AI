import re
from typing import Any, Optional

from src.services.retrieval_engine.domain.seai.models import RetrievalPlan


class EvidenceCardBuilder:
    def __init__(self, retrieval_repo):
        self.retrieval_repo = retrieval_repo

    def from_hits(self, vector_hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        atom_ids = unique([
            hit.get("metadata", {}).get("atom_id") or hit.get("object_id")
            for hit in vector_hits
            if hit.get("metadata", {}).get("object_type") == "atom"
        ])
        episode_ids = unique([
            hit.get("metadata", {}).get("episode_id") or hit.get("object_id")
            for hit in vector_hits
            if hit.get("metadata", {}).get("object_type") in {"atom", "episode"}
        ])

        distance_by_id: dict[str, float] = {}
        for hit in vector_hits:
            metadata = hit.get("metadata", {})
            object_id = metadata.get("atom_id") or metadata.get("episode_id") or hit.get("object_id")
            if object_id and hit.get("distance") is not None:
                if object_id not in distance_by_id or hit["distance"] < distance_by_id[object_id]:
                    distance_by_id[object_id] = hit["distance"]

        atoms = self.retrieval_repo.get_atoms_by_ids(atom_ids)
        episode_ids = unique([*episode_ids, *[atom["episode_id"] for atom in atoms]])
        episodes = self.retrieval_repo.get_episodes_by_ids(episode_ids)
        episode_by_id = {episode["id"]: episode for episode in episodes}
        # ponytail: include same-episode atoms so relation atoms can explain direct hits.
        atoms = dedupe_objects([*atoms, *self.retrieval_repo.get_atoms_by_episode_ids(episode_ids)])

        cards = [atom_card(atom, episode_by_id.get(atom["episode_id"]), distance_by_id.get(atom["id"])) for atom in atoms]
        cards.extend(episode_card(episode, distance_by_id.get(episode["id"])) for episode in episodes)
        return cards

    def lexical_sweep(self, query: str, plan: RetrievalPlan) -> list[dict[str, Any]]:
        if not hasattr(self.retrieval_repo, "search_episodes_by_terms"):
            return []
        # ponytail: broad questions need recall; cheap SQL LIKE fills gaps vector search misses.
        terms = important_terms([query, *plan.search_queries, *plan.must_find, *plan.constraints])
        episodes = self.retrieval_repo.search_episodes_by_terms(terms, limit=12)
        atoms = self.retrieval_repo.search_atoms_by_terms(terms, limit=16)
        episode_by_id = {episode["id"]: episode for episode in episodes}
        if atoms:
            linked = self.retrieval_repo.get_episodes_by_ids(unique([atom["episode_id"] for atom in atoms]))
            episode_by_id.update({episode["id"]: episode for episode in linked})

        cards = [atom_card(atom, episode_by_id.get(atom["episode_id"]), None) for atom in atoms]
        cards.extend(episode_card(episode, None) for episode in episode_by_id.values())
        return cards

    def from_subject_links(self, subject_links: list[dict[str, Any]]) -> list[dict[str, Any]]:
        atom_ids = unique([link.get("atom_id") for link in subject_links])
        episode_ids = unique([link.get("episode_id") for link in subject_links])
        atoms = self.retrieval_repo.get_atoms_by_ids(atom_ids)
        episodes = self.retrieval_repo.get_episodes_by_ids(unique([
            *episode_ids,
            *[atom["episode_id"] for atom in atoms],
        ]))
        episode_by_id = {episode["id"]: episode for episode in episodes}
        atom_by_id = {atom["id"]: atom for atom in atoms}
        link_by_atom = {link["atom_id"]: link for link in subject_links if link.get("atom_id")}
        link_by_episode = {link["episode_id"]: link for link in subject_links if not link.get("atom_id")}

        cards = []
        for atom_id, link in link_by_atom.items():
            atom = atom_by_id.get(atom_id)
            if atom:
                cards.append(subject_card(atom_card(atom, episode_by_id.get(atom["episode_id"]), None), link))
        for episode_id, link in link_by_episode.items():
            episode = episode_by_id.get(episode_id)
            if episode:
                cards.append(subject_card(episode_card(episode, None), link))
        return cards


def atom_card(atom: dict[str, Any], episode: dict[str, Any] | None, distance: float | None) -> dict[str, Any]:
    return {
        "evidence_id": f"atom:{atom['id']}",
        "object_type": "atom",
        "object_id": atom["id"],
        "episode_id": atom["episode_id"],
        "raw_input_id": atom["raw_input_id"],
        "atom_role": atom.get("atom_role"),
        "annotations": atom.get("annotations", []),
        "confidence": atom.get("confidence"),
        "content": atom.get("content"),
        "episode_summary": episode.get("summary") if episode else "",
        "citable_text": atom.get("evidence_text") or "",
        "spans": atom.get("evidence_spans", []),
        "distance": distance,
        "_object": atom,
    }


def episode_card(episode: dict[str, Any], distance: float | None) -> dict[str, Any]:
    return {
        "evidence_id": f"episode:{episode['id']}",
        "object_type": "episode",
        "object_id": episode["id"],
        "episode_id": episode["id"],
        "raw_input_id": episode["raw_input_id"],
        "content": episode.get("summary"),
        "episode_summary": episode.get("summary"),
        "citable_text": episode_snippets(episode),
        "spans": episode.get("spans", []),
        "distance": distance,
        "_object": episode,
    }


def subject_card(card: dict[str, Any], link: dict[str, Any]) -> dict[str, Any]:
    card["subject_id"] = link.get("subject_id")
    card["subject_name"] = link.get("subject_name")
    card["subject_kind"] = link.get("subject_kind")
    card["subject_relation"] = link.get("relation")
    card["subject_reason"] = link.get("reason")
    card["event_time"] = link.get("event_time")
    card["time_label"] = link.get("time_label")
    return card


def important_terms(values: list[str]) -> list[str]:
    stop = {"what", "was", "were", "with", "from", "that", "this", "like", "does", "over", "time", "answer", "text"}
    terms = []
    for value in values:
        for term in re.findall(r"[A-Za-z][A-Za-z']+", value):
            clean = term.strip("'")
            if clean.lower().endswith("'s"):
                clean = clean[:-2]
            if len(clean) < 4 or clean.lower() in stop:
                continue
            terms.append(clean)
    return unique(terms)[:10]


def episode_snippets(episode: dict[str, Any], per_span_budget: int = 900) -> str:
    raw_text = episode.get("raw_text") or ""
    snippets = []
    for span in episode.get("spans", []):
        text = raw_text[span["start"]:span["end"]]
        if len(text) > per_span_budget:
            text = f"{text[:per_span_budget]}..."
        snippets.append(text)
    return "\n...\n".join(snippets)


def card_matches_terms(card: dict[str, Any], terms: list[str]) -> bool:
    haystack = " ".join([
        str(card.get("content") or ""),
        str(card.get("episode_summary") or ""),
        str(card.get("citable_text") or ""),
        " ".join(card.get("annotations") or []),
    ]).lower()
    return any(term.lower() in haystack for term in terms)


def unique(values: list[Optional[str]]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def dedupe_objects(objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    result = []
    for item in objects:
        item_id = item.get("id")
        if item_id and item_id not in seen:
            seen.add(item_id)
            result.append(item)
    return result
