from __future__ import annotations

import json
import re
from typing import Any

from src.infra.sqlite import get_connection
from src.repositories import retrieval_index
from src.services.rag.models import SourceChunk

_ATTRIBUTE_TRIGGERS = {
    "appearance", "appearances", "attribute", "attributes", "body", "build",
    "characteristic", "characteristics", "count", "counts", "description",
    "described", "detail", "details", "face", "feature", "features", "look",
    "looks", "mark", "marks", "mole", "moles", "number", "numbers",
    "physical", "property", "properties", "quality", "qualities", "spec",
    "specs", "trait", "traits",
}
_ATTRIBUTE_EXPANSIONS = (
    "attribute", "attributes", "detail", "details", "descriptor",
    "descriptors", "label", "labels", "count", "counts", "number", "numbers",
    "feature", "features", "property", "properties", "measurement",
    "measurements", "appearance", "physical", "body", "face", "hair", "eyes",
    "eye", "skin", "height", "build", "scar", "scars", "mole", "moles",
    "mark", "marks", "birthmark", "birthmarks", "freckle", "freckles",
    "complexion", "tattoo", "tattoos", "piercing", "piercings",
)
_COMPARISON_TRIGGERS = {
    "compare", "comparison", "contrast", "contrasts", "different",
    "difference", "differences", "dissimilar", "dissimilarities", "parallel",
    "parallels", "same", "similar", "similarities", "similarity", "versus",
    "vs",
}
_COMPARISON_EXPANSIONS = (
    "attribute", "attributes", "context", "background", "behavior", "change",
    "changes", "goal", "goals", "constraint", "constraints", "relationship",
    "relationships", "decision", "decisions", "outcome", "outcomes",
    "parallels", "contrast",
)
_REASONING_TRIGGERS = {
    "cause", "causes", "changed", "changes", "developed", "development",
    "effect", "effects", "evolved", "evolution", "impact", "impacts",
    "reason", "reasons", "timeline", "why",
}
_REASONING_EXPANSIONS = (
    "evidence", "context", "background", "cause", "causes", "effect",
    "effects", "change", "changes", "outcome", "outcomes", "sequence",
    "before", "after", "because",
)


def save_many(chunks: list[SourceChunk]) -> None:
    """Store citable chunks with JSON-encoded spans and metadata."""
    if not chunks:
        return
    conn = get_connection()
    conn.executemany(
        """
        INSERT INTO source_chunks (id, raw_input_id, text, summary, spans, source_time, user_id, metadata, directory_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                chunk["user_id"],
                json.dumps(chunk.get("metadata", {}), ensure_ascii=False),
                chunk.get("directory_path"),
            )
            for chunk in chunks
        ],
    )
    for user_id in {chunk.get("user_id") for chunk in chunks}:
        retrieval_index.bump(user_id, conn)
    conn.commit()


def get_by_ids(chunk_ids: list[str], user_id: str) -> list[dict[str, Any]]:
    """Load chunks in caller-provided order.

    Retrieval will need this later when vector search returns IDs in ranked order.
    """
    ids = [chunk_id for chunk_id in dict.fromkeys(chunk_ids) if chunk_id]
    if not ids:
        return []
    placeholders = ",".join(["?"] * len(ids))
    rows = get_connection().execute(
        f"""
        SELECT sc.id, sc.raw_input_id, ri.job_id as note_id, sc.text, sc.summary, sc.spans, sc.source_time, sc.user_id, sc.metadata, sc.created_at, sc.directory_path
        FROM source_chunks sc
        JOIN raw_inputs ri ON ri.id = sc.raw_input_id
        WHERE sc.id IN ({placeholders}) AND sc.user_id = ? AND ri.deleted_at IS NULL
        """,
        [*ids, user_id],
    ).fetchall()
    by_id = {_from_row(row)["id"]: _from_row(row) for row in rows}
    return [by_id[chunk_id] for chunk_id in ids if chunk_id in by_id]


def update_directory_path(raw_input_id: str, new_path: str | None) -> bool:
    """Update directory_path for all chunks of a raw input."""
    conn = get_connection()
    user_rows = conn.execute(
        "SELECT DISTINCT user_id FROM source_chunks WHERE raw_input_id = ?",
        (raw_input_id,),
    ).fetchall()
    cursor = conn.execute(
        "UPDATE source_chunks SET directory_path = ? WHERE raw_input_id = ?",
        (new_path, raw_input_id)
    )
    if cursor.rowcount > 0:
        for row in user_rows:
            retrieval_index.bump(row["user_id"], conn)
    conn.commit()
    return cursor.rowcount > 0


def get_by_raw_input_id(raw_input_id: str) -> list[dict[str, Any]]:
    """Load all chunks already saved for one raw input."""
    rows = get_connection().execute(
        """
        SELECT sc.id, sc.raw_input_id, ri.job_id as note_id, sc.text, sc.summary, sc.spans, sc.source_time, sc.user_id, sc.metadata, sc.created_at, sc.directory_path
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
    user_rows = conn.execute(
        "SELECT DISTINCT user_id FROM source_chunks WHERE raw_input_id = ?",
        (raw_input_id,),
    ).fetchall()
    conn.execute("DELETE FROM source_chunks WHERE raw_input_id = ?", (raw_input_id,))
    for row in user_rows:
        retrieval_index.bump(row["user_id"], conn)
    conn.commit()


def delete_all(user_id: str) -> None:
    """Wipe all source chunks for a user when reindexing."""
    conn = get_connection()
    conn.execute("DELETE FROM source_chunks WHERE user_id = ?", (user_id,))
    retrieval_index.bump(user_id, conn)
    conn.commit()


def search(query: str, user_id: str, limit: int = 8, within_directories: list[str] | None = None, excluding_directories: list[str] | None = None, within_tags: list[str] | None = None, excluding_tags: list[str] | None = None, within_tags_condition: str = "any") -> list[dict[str, Any]]:
    """Small lexical fallback over source text and summaries."""
    terms = _terms(query)
    if not terms:
        return []
        
    terms_clause = "(" + " OR ".join(["(sc.text LIKE ? OR sc.summary LIKE ?)"] * len(terms)) + ")"
    score_sql = " + ".join(["CASE WHEN sc.text LIKE ? OR sc.summary LIKE ? THEN 1 ELSE 0 END"] * len(terms))
    where_clauses = [terms_clause, "sc.user_id = ?", "ri.deleted_at IS NULL"]
    
    score_params = []
    params = []
    for term in terms:
        score_params.extend([f"%{term}%", f"%{term}%"])
        params.extend([f"%{term}%", f"%{term}%"])
    params.append(user_id)
    
    if within_directories:
        dir_clauses = []
        for path in within_directories:
            dir_clauses.append("sc.directory_path LIKE ?")
            params.append(f"{path}%")
        where_clauses.append(f"({' OR '.join(dir_clauses)})")
        
    if excluding_directories:
        for path in excluding_directories:
            where_clauses.append("(sc.directory_path NOT LIKE ? OR sc.directory_path IS NULL)")
            params.append(f"{path}%")
            
    if within_tags:
        placeholders = ",".join(["?"] * len(within_tags))
        if within_tags_condition == "all":
            where_clauses.append(f"ri.job_id IN (SELECT note_id FROM note_tags WHERE tag_id IN ({placeholders}) GROUP BY note_id HAVING COUNT(DISTINCT tag_id) = ?)")
            params.extend(within_tags)
            params.append(len(within_tags))
        else:
            where_clauses.append(f"ri.job_id IN (SELECT note_id FROM note_tags WHERE tag_id IN ({placeholders}))")
            params.extend(within_tags)
            
    if excluding_tags:
        placeholders = ",".join(["?"] * len(excluding_tags))
        where_clauses.append(f"ri.job_id NOT IN (SELECT note_id FROM note_tags WHERE tag_id IN ({placeholders}))")
        params.extend(excluding_tags)
            
    where_sql = " AND ".join(where_clauses)
    
    rows = get_connection().execute(
        f"""
        SELECT sc.id, sc.raw_input_id, ri.job_id as note_id, sc.text, sc.summary, sc.spans, sc.source_time, sc.user_id, sc.metadata, sc.created_at, sc.directory_path,
               ({score_sql}) as lexical_score
        FROM source_chunks sc
        JOIN raw_inputs ri ON ri.id = sc.raw_input_id
        WHERE {where_sql}
        ORDER BY lexical_score DESC, sc.created_at DESC
        LIMIT ?
        """,
        [*score_params, *params, limit],
    ).fetchall()
    return [_from_row(row) for row in rows]


def list_with_raw_inputs(user_id: str | None = None) -> dict[str, Any]:
    """Dev view: raw inputs with nested source chunks."""
    conn = get_connection()
    raw_where = "WHERE deleted_at IS NULL"
    raw_params: list[Any] = []
    if user_id:
        raw_where += " AND user_id = ?"
        raw_params.append(user_id)
    raw_inputs = [
        dict(row)
        for row in conn.execute(
            f"SELECT id, job_id, content, user_id, created_at FROM raw_inputs {raw_where} ORDER BY created_at DESC",
            raw_params,
        )
    ]
    chunk_where = ""
    chunk_params: list[Any] = []
    if user_id:
        chunk_where = "WHERE user_id = ?"
        chunk_params.append(user_id)
    chunks = [
        _from_row(row)
        for row in conn.execute(
            f"""
            SELECT id, raw_input_id, text, summary, spans, source_time, user_id, metadata, created_at, directory_path
            FROM source_chunks
            {chunk_where}
            ORDER BY created_at ASC
            """,
            chunk_params,
        )
    ]
    chunks_by_raw: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunks:
        chunks_by_raw.setdefault(chunk["raw_input_id"], []).append(chunk)
    for raw_input in raw_inputs:
        raw_input["source_chunks"] = chunks_by_raw.get(raw_input["id"], [])
    return {"total_raw_inputs": len(raw_inputs), "total_source_chunks": len(chunks), "data": raw_inputs}


def get_paginated_for_note(note_id: str, user_id: str, page: int = 1, limit: int = 10) -> dict[str, Any]:
    """Load paginated chunks for a specific note along with their recall links."""
    conn = get_connection()
    offset = max(0, (page - 1) * limit)

    count_row = conn.execute(
        """
        SELECT COUNT(*) as c
        FROM source_chunks sc
        JOIN raw_inputs ri ON ri.id = sc.raw_input_id
        WHERE ri.job_id = ? AND sc.user_id = ? AND ri.deleted_at IS NULL
        """,
        (note_id, user_id)
    ).fetchone()
    total = count_row["c"] if count_row else 0

    chunk_rows = conn.execute(
        """
        SELECT sc.id, sc.raw_input_id, ri.job_id as note_id, sc.text, sc.summary, sc.spans, sc.source_time, sc.user_id, sc.metadata, sc.created_at, sc.directory_path
        FROM source_chunks sc
        JOIN raw_inputs ri ON ri.id = sc.raw_input_id
        WHERE ri.job_id = ? AND sc.user_id = ? AND ri.deleted_at IS NULL
        ORDER BY sc.created_at ASC
        LIMIT ? OFFSET ?
        """,
        (note_id, user_id, limit, offset)
    ).fetchall()

    chunks = [_from_row(row) for row in chunk_rows]
    if not chunks:
        return {"total": total, "page": page, "limit": limit, "chunks": []}

    chunk_ids = [c["id"] for c in chunks]
    placeholders = ",".join(["?"] * len(chunk_ids))

    for c in chunks:
        c["recall_links"] = []

    link_rows = conn.execute(
        f"""
        SELECT l.id, l.recall_key_id, l.source_chunk_id, l.relation, l.relation_label, l.confidence, l.reason, l.event_time, l.time_label,
               k.name, k.kind, k.kind_label
        FROM recall_links l
        JOIN recall_keys k ON k.id = l.recall_key_id
        WHERE l.source_chunk_id IN ({placeholders}) AND l.user_id = ?
        ORDER BY l.created_at DESC
        """,
        [*chunk_ids, user_id]
    ).fetchall()

    chunk_map = {c["id"]: c for c in chunks}
    for row in link_rows:
        chunk_map[row["source_chunk_id"]]["recall_links"].append(dict(row))

    return {"total": total, "page": page, "limit": limit, "chunks": chunks}


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
    if seen & _ATTRIBUTE_TRIGGERS:
        for term in _ATTRIBUTE_EXPANSIONS:
            if term not in seen:
                seen.add(term)
                terms.append(term)
    if seen & _COMPARISON_TRIGGERS:
        for term in _COMPARISON_EXPANSIONS:
            if term not in seen:
                seen.add(term)
                terms.append(term)
    if seen & _REASONING_TRIGGERS:
        for term in _REASONING_EXPANSIONS:
            if term not in seen:
                seen.add(term)
                terms.append(term)
    return terms[:36]
