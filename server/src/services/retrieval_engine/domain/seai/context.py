from typing import Any

from src.services.retrieval_engine.domain.seai.cards import card_matches_terms, important_terms


def is_broad_query(query: str) -> bool:
    lowered = query.lower()
    broad_terms = ["worldview", "overall", "broad", "summarize", "explain", "development", "early", "relationship"]
    return any(term in lowered for term in broad_terms) or lowered.startswith(("what was", "what is", "tell me"))


def broaden_context_cards(
    query: str,
    selected_cards: list[dict[str, Any]],
    all_cards: list[dict[str, Any]],
    trace: dict[str, Any],
) -> list[dict[str, Any]]:
    missing = any(round_info.get("missing_aspects") for round_info in trace.get("rounds", []))
    if not missing and not is_broad_query(query):
        return selected_cards

    selected_ids = {card["evidence_id"] for card in selected_cards}
    result = list(selected_cards)
    query_terms = important_terms([query])
    candidates = sorted(
        all_cards,
        key=lambda card: (
            card["evidence_id"] in selected_ids,
            card["object_type"] != "episode",
            card.get("distance") is None,
            card.get("distance") or 0.0,
        )
    )
    for card in candidates:
        if card["evidence_id"] in selected_ids:
            continue
        if query_terms and not card_matches_terms(card, query_terms):
            continue
        result.append(card)
        selected_ids.add(card["evidence_id"])
        if len(result) >= 10:
            break
    trace["context_broadened"] = len(result) > len(selected_cards)
    return result


def pack_evidence_context(cards: list[dict[str, Any]], char_budget: int = 9000, strict: bool = False) -> str:
    header = "QUOTE BANK: cite only UUIDs after [QUOTE ...] and copy exact QUOTE text.\n\n"
    if strict:
        header = (
            "STRICT RETRY QUOTE BANK: cite only UUIDs after [QUOTE ...]. "
            "Every exact_quote must be copied from a QUOTE block exactly.\n\n"
        )
    blocks = [header]
    used = len(header)

    for card in cards:
        quote = card.get("citable_text") or ""
        if card["object_type"] == "atom":
            block = (
                f"[QUOTE {card['object_id']}]\n"
                f"TYPE: atom\n"
                f"SOURCE: {card.get('raw_input_id')}\n"
                f"EPISODE: {card.get('episode_id')}\n"
                f"ROLE: {card.get('atom_role')} CONFIDENCE: {card.get('confidence')}\n"
                f"ANNOTATIONS: {', '.join(card.get('annotations') or [])}\n"
                f"HINT (not citable): {card.get('content') or ''}\n"
                f"QUOTE:\n{quote}\n"
            )
        else:
            block = (
                f"[QUOTE {card['object_id']}]\n"
                f"TYPE: episode\n"
                f"SOURCE: {card.get('raw_input_id')}\n"
                f"HINT (not citable): {card.get('episode_summary') or ''}\n"
                f"QUOTE:\n{quote}\n"
            )

        remaining = char_budget - used
        if remaining <= 0:
            break
        if len(block) > remaining:
            if len(blocks) == 1:
                blocks.append(block[:remaining])
            break
        blocks.append(block)
        used += len(block)

    return "\n---\n".join(blocks)


def pack_legacy_context(chunks: list[dict[str, Any]], char_budget: int = 12000) -> str:
    blocks = []
    used = 0
    for chunk in chunks:
        block = (
            f"[CHUNK {chunk['id']}]\n"
            f"SOURCE: {chunk.get('source_input_id')}\n"
            f"OFFSETS: {chunk.get('start_char')}-{chunk.get('end_char')}\n"
            f"LEVEL: {chunk.get('level', 0)} PARENT: {chunk.get('parent_id') or 'none'}\n"
            f"SUMMARY (not citable): {chunk.get('summary') or ''}\n"
            f"CHUNK TEXT:\n{chunk.get('text') or ''}\n"
        )
        if used + len(block) > char_budget:
            break
        blocks.append(block)
        used += len(block)
    return "\n---\n".join(blocks)


def objects_from_cards(cards: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    episodes, atoms = [], []
    seen_episodes, seen_atoms = set(), set()
    for card in cards:
        obj = card.get("_object")
        if not obj:
            continue
        if card["object_type"] == "episode" and obj["id"] not in seen_episodes:
            seen_episodes.add(obj["id"])
            episodes.append(obj)
        if card["object_type"] == "atom" and obj["id"] not in seen_atoms:
            seen_atoms.add(obj["id"])
            atoms.append(obj)
    return episodes, atoms
