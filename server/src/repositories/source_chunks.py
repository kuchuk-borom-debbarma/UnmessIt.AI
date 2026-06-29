from __future__ import annotations

import json
import re
from typing import Any

from src.infra.sqlite import get_connection
from src.services.rag.models import SourceChunk


def save_many(chunks: list[SourceChunk]) -> None:
    """Store citable chunks with JSON-encoded spans and metadata."""
    if not chunks:
        return
    conn = get_connection()
    conn.executemany(
        """
        INSERT INTO source_chunks (id, raw_input_id, text, summary, spans, source_time, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO NOTHING
        """,
        [
            (
                chunk["id"],
                chunk["raw_input_id"],
                chunk["text"],
                chunk["summary"],
                json.dumps(chunk["spans"], ensure_ascii=False),
                chunk.get("source_time"),
                json.dumps(chunk.get("metadata", {}), ensure_ascii=False),
            )
            for chunk in chunks
        ],
    )
    conn.commit()


def get_by_ids(chunk_ids: list[str]) -> list[dict[str, Any]]:
    """Load chunks in caller-provided order.

    Retrieval will need this later when vector search returns IDs in ranked order.
    """
    ids = [chunk_id for chunk_id in dict.fromkeys(chunk_ids) if chunk_id]
    if not ids:
        return []
    placeholders = ",".join(["?"] * len(ids))
    rows = get_connection().execute(
        f"""
        SELECT sc.id, sc.raw_input_id, sc.text, sc.summary, sc.spans, sc.source_time, sc.metadata, sc.created_at
        FROM source_chunks sc
        JOIN raw_inputs ri ON ri.id = sc.raw_input_id
        WHERE sc.id IN ({placeholders}) AND ri.deleted_at IS NULL
        """,
        ids,
    ).fetchall()
    by_id = {_from_row(row)["id"]: _from_row(row) for row in rows}
    return [by_id[chunk_id] for chunk_id in ids if chunk_id in by_id]


def get_by_raw_input_id(raw_input_id: str) -> list[dict[str, Any]]:
    """Load all chunks already saved for one raw input."""
    rows = get_connection().execute(
        """
        SELECT sc.id, sc.raw_input_id, sc.text, sc.summary, sc.spans, sc.source_time, sc.metadata, sc.created_at
        FROM source_chunks sc
        JOIN raw_inputs ri ON ri.id = sc.raw_input_id
        WHERE sc.raw_input_id = ? AND ri.deleted_at IS NULL
        ORDER BY sc.created_at ASC
        """,
        (raw_input_id,),
    ).fetchall()
    return [_from_row(row) for row in rows]


def delete_by_raw_input_id(raw_input_id: str) -> None:
    """Delete source chunks owned by a corrupt job's raw input."""
    conn = get_connection()
    conn.execute("DELETE FROM source_chunks WHERE raw_input_id = ?", (raw_input_id,))
    conn.commit()


def search(query: str, limit: int = 8) -> list[dict[str, Any]]:
    """Small lexical fallback over source text and summaries."""
    terms = _terms(query)
    if not terms:
        return []
    where = " OR ".join(["(text LIKE ? OR summary LIKE ?)"] * len(terms))
    params = []
    for term in terms:
        params.extend([f"%{term}%", f"%{term}%"])
    rows = get_connection().execute(
        f"""
        SELECT sc.id, sc.raw_input_id, sc.text, sc.summary, sc.spans, sc.source_time, sc.metadata, sc.created_at
        FROM source_chunks sc
        JOIN raw_inputs ri ON ri.id = sc.raw_input_id
        WHERE ({where}) AND ri.deleted_at IS NULL
        ORDER BY sc.created_at DESC
        LIMIT ?
        """,
        [*params, limit],
    ).fetchall()
    return [_from_row(row) for row in rows]


def list_with_raw_inputs() -> dict[str, Any]:
    """Dev view: raw inputs with nested source chunks."""
    conn = get_connection()
    raw_inputs = [dict(row) for row in conn.execute("SELECT id, job_id, content, created_at FROM raw_inputs WHERE deleted_at IS NULL ORDER BY created_at DESC")]
    chunks = [
        _from_row(row)
        for row in conn.execute(
            """
            SELECT id, raw_input_id, text, summary, spans, source_time, metadata, created_at
            FROM source_chunks
            ORDER BY created_at ASC
            """
        )
    ]
    chunks_by_raw: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunks:
        chunks_by_raw.setdefault(chunk["raw_input_id"], []).append(chunk)
    for raw_input in raw_inputs:
        raw_input["source_chunks"] = chunks_by_raw.get(raw_input["id"], [])
    return {"total_raw_inputs": len(raw_inputs), "total_source_chunks": len(chunks), "data": raw_inputs}


def _from_row(row) -> dict[str, Any]:
    """Decode SQLite JSON columns into Python values."""
    chunk = dict(row)
    chunk["spans"] = _json(chunk.get("spans"), [])
    chunk["metadata"] = _json(chunk.get("metadata"), {})
    return chunk


def _json(value: Any, fallback: Any) -> Any:
    try:
        return json.loads(value) if value else fallback
    except (TypeError, json.JSONDecodeError):
        return fallback


def _terms(query: str) -> list[str]:
    """Cheap query token cleanup for LIKE search."""
    seen = set()
    terms = []
    for clean in re.findall(r"[A-Za-z0-9]+", query):
        lowered = clean.lower()
        if len(clean) >= 3 and lowered not in seen:
            seen.add(lowered)
            terms.append(clean)
    return terms[:8]
