from typing import Optional

from src.services.retrieval_engine.domain.seai.models import CitedAnswer


def validated_legacy_response(answer: CitedAnswer, chunks: list[dict]) -> dict:
    chunk_by_id = {chunk["id"]: chunk for chunk in chunks}
    citations = []

    for citation in answer.citations:
        chunk = chunk_by_id.get(citation.statement_id)
        if not chunk:
            return {"answer": "No sourced answer found.", "citations": []}

        quote = citation.exact_quote.strip()
        if not quote or quote not in (chunk.get("text") or ""):
            return {"answer": "No sourced answer found.", "citations": []}

        citations.append({
            "statement_id": chunk["id"],
            "source_input_id": chunk.get("source_input_id"),
            "start_char": chunk.get("start_char"),
            "end_char": chunk.get("end_char"),
            "exact_quote": quote,
            "raw_text": chunk.get("text"),
            "cleaned_text": chunk.get("summary"),
        })

    if not citations and answer.answer_text != "No sourced answer found.":
        return {"answer": "No sourced answer found.", "citations": []}

    return {"answer": answer.answer_text, "citations": citations}


def validated_seai_response(answer: CitedAnswer, episodes: list[dict], atoms: list[dict]) -> dict:
    objects = {episode["id"]: ("episode", episode) for episode in episodes}
    objects.update({atom["id"]: ("atom", atom) for atom in atoms})
    citations = []

    for citation in answer.citations:
        quote = citation.exact_quote.strip()
        entry = objects.get(citation.statement_id)
        match = None
        if entry:
            object_type, obj = entry
            spans = obj.get("evidence_spans") if object_type == "atom" else obj.get("spans")
            match = find_quote_in_spans(obj.get("raw_text") or "", spans or [], quote)
        else:
            object_type, obj = None, None
            for candidate_type, candidate in objects.values():
                spans = candidate.get("evidence_spans") if candidate_type == "atom" else candidate.get("spans")
                match = find_quote_in_spans(candidate.get("raw_text") or "", spans or [], quote)
                if match:
                    object_type, obj = candidate_type, candidate
                    break

        if not obj:
            return {"answer": "No sourced answer found.", "citations": []}

        spans = obj.get("evidence_spans") if object_type == "atom" else obj.get("spans")
        match = match or find_quote_in_spans(obj.get("raw_text") or "", spans or [], quote)
        if not quote or not match:
            return {"answer": "No sourced answer found.", "citations": []}

        citations.append({
            "statement_id": obj["id"],
            "source_input_id": obj.get("raw_input_id"),
            "start_char": match["start"],
            "end_char": match["end"],
            "spans": [match],
            "exact_quote": quote,
            "raw_text": obj.get("evidence_text") if object_type == "atom" else obj.get("text"),
            "cleaned_text": obj.get("content") if object_type == "atom" else obj.get("summary"),
            "object_type": object_type,
        })

    if not citations and answer.answer_text != "No sourced answer found.":
        return {"answer": "No sourced answer found.", "citations": []}

    return {"answer": answer.answer_text, "citations": citations}


def find_quote_in_spans(raw_text: str, spans: list[dict[str, int]], quote: str) -> Optional[dict[str, int]]:
    for span in spans:
        idx = raw_text.find(quote, span["start"], span["end"])
        if idx != -1:
            return {"start": idx, "end": idx + len(quote)}
    return None
