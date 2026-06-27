from __future__ import annotations

from typing import Any

from src.services.ingest_engine.domain.seai.models import EpisodeDraft, SourceWindow, Span


def extract_atom_list(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    atoms = data.get("atoms") or data.get("kept_atoms") or data.get("verified_atoms") or []
    return atoms if isinstance(atoms, list) else []


def episode_quotes(draft: EpisodeDraft) -> list[str]:
    quotes = draft.get("evidence_quotes") or draft.get("quotes") or draft.get("spans") or []
    if isinstance(quotes, str):
        quotes = [quotes]
    if not quotes and draft.get("text"):
        quotes = [draft["text"]]
    return [str(quote).strip() for quote in quotes if str(quote).strip()]


def atom_quotes(draft: dict[str, Any]) -> list[str]:
    quotes = draft.get("evidence_quotes") or draft.get("evidence_spans") or draft.get("evidence_span") or []
    if isinstance(quotes, str):
        quotes = [quotes]
    return [str(quote).strip() for quote in quotes if str(quote).strip()]


def annotations(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [part.strip() for part in value.split(",")]
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def find_quote_spans(
    raw_text: str,
    quotes: list[str],
    allowed_spans: list[Span] | None = None,
) -> list[Span]:
    spans = []
    cursor = 0
    for quote in quotes:
        found = None
        search_spans = allowed_spans or [{"start": 0, "end": len(raw_text)}]
        for allowed in search_spans:
            start = max(allowed["start"], cursor if allowed_spans is None else allowed["start"])
            idx = raw_text.find(quote, start, allowed["end"])
            if idx != -1:
                found = {"start": idx, "end": idx + len(quote)}
                break
        if found is None and allowed_spans is None:
            idx = raw_text.find(quote)
            if idx != -1:
                found = {"start": idx, "end": idx + len(quote)}
        if found is not None:
            spans.append(found)
            cursor = found["end"]
    return spans


def merge_spans(spans: list[Span]) -> list[Span]:
    if not spans:
        return []
    merged = []
    for span in sorted(spans, key=lambda item: item["start"]):
        if not merged or span["start"] > merged[-1]["end"]:
            merged.append(dict(span))
        else:
            merged[-1]["end"] = max(merged[-1]["end"], span["end"])
    return merged


def stitch_spans(raw_text: str, spans: list[Span]) -> str:
    return "\n...\n".join(raw_text[span["start"]:span["end"]] for span in spans)


class EvidenceResolver:
    def episode_spans(self, raw_text: str, draft: EpisodeDraft, window: SourceWindow) -> list[Span]:
        return merge_spans(find_quote_spans(
            raw_text,
            episode_quotes(draft),
            [{"start": window["start_idx"], "end": window["end_idx"]}],
        ))

    def episode_text(self, raw_text: str, spans: list[Span]) -> str:
        return stitch_spans(raw_text, spans)
