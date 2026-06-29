from __future__ import annotations

import json
import re
from typing import Any

from src.infra.sqlite import get_connection
from src.services.rag.models import RecallIndex


def find_candidate_keys(terms: list[str], limit: int = 20) -> list[dict[str, Any]]:
    """Find existing keys by exact term and keyword search before creating new ones."""
    terms = _clean_terms(terms)
    if not terms:
        return []
    exact = _merge_candidates(find_exact_term_matches(terms, limit=limit), limit)
    remaining = max(0, limit - len(exact))
    fts = find_fts_matches(terms, limit=remaining) if remaining else []
    return _merge_candidates([*exact, *fts], limit)


def has_keys() -> bool:
    """Return whether semantic recall-key lookup has anything useful to search."""
    row = get_connection().execute("SELECT 1 FROM recall_keys LIMIT 1").fetchone()
    return row is not None


def find_exact_term_matches(terms: list[str], limit: int = 20) -> list[dict[str, Any]]:
    """Find keys whose saved name or alias exactly matches a normalized term."""
    normalized_terms = _normalized_terms(terms)
    if not normalized_terms:
        return []
    placeholders = ", ".join("?" for _ in normalized_terms)
    rows = get_connection().execute(
        f"""
        SELECT k.id, k.name, k.kind, k.kind_label, k.aliases, k.summary, k.metadata,
               k.created_at, k.updated_at, t.term AS match_text, t.term_type
        FROM recall_key_terms t
        JOIN recall_keys k ON k.id = t.recall_key_id
        WHERE t.normalized_term IN ({placeholders})
        ORDER BY CASE t.term_type WHEN 'name' THEN 0 ELSE 1 END, k.updated_at DESC
        LIMIT ?
        """,
        [*normalized_terms, limit],
    ).fetchall()
    return [_candidate(row, "exact", f"exact {row['term_type']} match: {row['match_text']}") for row in rows]


def find_fts_matches(terms: list[str], limit: int = 20) -> list[dict[str, Any]]:
    """Find keyword matches without scanning every recall key row."""
    if limit <= 0:
        return []
    query = _fts_query(terms)
    if not query:
        return []

    rows = get_connection().execute(
        """
        SELECT k.id, k.name, k.kind, k.kind_label, k.aliases, k.summary, k.metadata,
               k.created_at, k.updated_at
        FROM recall_keys_fts f
        JOIN recall_keys k ON k.id = f.recall_key_id
        WHERE recall_keys_fts MATCH ?
        ORDER BY bm25(recall_keys_fts), k.updated_at DESC
        LIMIT ?
        """,
        [query, limit],
    ).fetchall()
    return [_candidate(row, "keyword", "keyword match in name, aliases, summary, or label") for row in rows]


def find_keys_by_ids(ids: list[str]) -> list[dict[str, Any]]:
    """Load recall keys by ID while preserving the requested order."""
    clean_ids = [str(item) for item in ids if str(item)]
    if not clean_ids:
        return []
    placeholders = ", ".join("?" for _ in clean_ids)
    rows = get_connection().execute(
        f"""
        SELECT id, name, kind, kind_label, aliases, summary, metadata, created_at, updated_at
        FROM recall_keys
        WHERE id IN ({placeholders})
        """,
        clean_ids,
    ).fetchall()
    key_by_id = {row["id"]: _key_from_row(row) for row in rows}
    return [key_by_id[item] for item in clean_ids if item in key_by_id]


def find_keys_by_names(names: list[str]) -> list[dict[str, Any]]:
    """Find recall keys whose name or aliases match any of the given subject names.

    Uses FTS5 search so diacritic variants match: 'Helene' finds 'Hélène',
    'Boris' finds 'Borís', etc. Domain-neutral: names come from the subjects
    extraction node.
    """
    if not names:
        return []
    seen: dict[str, dict[str, Any]] = {}
    conn = get_connection()
    for name in names:
        # Escape FTS special chars; wrap in quotes for exact phrase match.
        safe = name.replace('"', '""')
        try:
            rows = conn.execute(
                """
                SELECT rk.id, rk.name, rk.kind, rk.kind_label, rk.aliases,
                       rk.summary, rk.metadata, rk.created_at, rk.updated_at
                FROM recall_keys_fts fts
                JOIN recall_keys rk ON rk.id = fts.recall_key_id
                WHERE recall_keys_fts MATCH ?
                """,
                (safe,),
            ).fetchall()
            for row in rows:
                seen.setdefault(row["id"], _key_from_row(row))
        except Exception:
            pass  # ponytail: bad FTS term → skip, not a fatal error
    return list(seen.values())



def source_chunks_with_links(source_chunk_ids: list[str]) -> set[str]:
    """Return source chunk IDs that already have recall evidence links."""
    clean_ids = [chunk_id for chunk_id in dict.fromkeys(source_chunk_ids) if chunk_id]
    if not clean_ids:
        return set()
    placeholders = ", ".join("?" for _ in clean_ids)
    rows = get_connection().execute(
        f"SELECT DISTINCT source_chunk_id FROM recall_links WHERE source_chunk_id IN ({placeholders})",
        clean_ids,
    ).fetchall()
    return {row["source_chunk_id"] for row in rows}


def keys_for_source_chunks(source_chunk_ids: list[str]) -> list[dict[str, Any]]:
    """Load recall keys connected to the given source chunks."""
    clean_ids = [chunk_id for chunk_id in dict.fromkeys(source_chunk_ids) if chunk_id]
    if not clean_ids:
        return []
    placeholders = ", ".join("?" for _ in clean_ids)
    rows = get_connection().execute(
        f"""
        SELECT DISTINCT k.id, k.name, k.kind, k.kind_label, k.aliases, k.summary,
               k.metadata, k.created_at, k.updated_at
        FROM recall_keys k
        JOIN recall_links l ON l.recall_key_id = k.id
        WHERE l.source_chunk_id IN ({placeholders})
        ORDER BY k.updated_at DESC
        """,
        clean_ids,
    ).fetchall()
    return [_key_from_row(row) for row in rows]


def linked_source_chunk_ids(recall_key_ids: list[str], limit: int = 12) -> list[str]:
    """Return chunks connected to recall keys for one-hop query expansion."""
    clean_ids = [key_id for key_id in dict.fromkeys(recall_key_ids) if key_id]
    if not clean_ids or limit <= 0:
        return []
    placeholders = ", ".join("?" for _ in clean_ids)
    rows = get_connection().execute(
        f"""
        SELECT c.id, MIN(c.created_at) AS first_seen
        FROM source_chunks c
        JOIN recall_links l ON l.source_chunk_id = c.id
        WHERE l.recall_key_id IN ({placeholders})
        GROUP BY c.id
        ORDER BY first_seen ASC
        LIMIT ?
        """,
        [*clean_ids, limit],
    ).fetchall()
    return [row["id"] for row in rows]


def save_index(index: RecallIndex) -> int:
    """Save keys and append only new key-to-chunk evidence links."""
    keys = index.get("recall_keys", [])
    links = index.get("recall_links", [])
    if not keys and not links:
        return 0

    conn = get_connection()
    for key in keys:
        # Upsert by key ID: reused keys are updated, while truly new keys are inserted.
        conn.execute(
            """
            INSERT INTO recall_keys (id, name, kind, kind_label, aliases, summary, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = recall_keys.name,
                kind = CASE WHEN recall_keys.kind = 'other' THEN excluded.kind ELSE recall_keys.kind END,
                kind_label = COALESCE(excluded.kind_label, recall_keys.kind_label),
                aliases = excluded.aliases,
                summary = CASE WHEN excluded.summary != '' THEN excluded.summary ELSE recall_keys.summary END,
                metadata = excluded.metadata,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                key["id"],
                key["name"],
                key["kind"],
                key.get("kind_label"),
                json.dumps(key.get("aliases", []), ensure_ascii=False),
                key.get("summary", ""),
                json.dumps(key.get("metadata", {}), ensure_ascii=False),
            ),
        )
        _save_lookup_rows(conn, key)

    saved_links = 0
    for link in links:
        # The DB unique constraint is the final guard against storing the same evidence twice.
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO recall_links
                (id, recall_key_id, source_chunk_id, relation, relation_label,
                 confidence, reason, event_time, time_label, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                link["id"],
                link["recall_key_id"],
                link["source_chunk_id"],
                link["relation"],
                link.get("relation_label") or "",
                link["confidence"],
                link.get("reason", ""),
                link.get("event_time"),
                link.get("time_label"),
                json.dumps(link.get("metadata", {}), ensure_ascii=False),
            ),
        )
        saved_links += cursor.rowcount
    conn.commit()
    return saved_links


def get_view() -> dict[str, Any]:
    """Dev view: recall keys with their linked source chunk evidence."""
    conn = get_connection()
    keys = []
    for row in conn.execute(
        """
        SELECT
            k.id, k.name, k.kind, k.kind_label, k.aliases, k.summary, k.metadata,
            k.created_at, k.updated_at,
            COUNT(l.id) AS link_count,
            MAX(COALESCE(l.event_time, l.created_at)) AS latest_link_time
        FROM recall_keys k
        LEFT JOIN recall_links l ON l.recall_key_id = k.id
        GROUP BY k.id
        ORDER BY latest_link_time DESC, k.updated_at DESC
        """
    ):
        key = _key_from_row(row)
        key["link_count"] = row["link_count"]
        key["latest_link_time"] = row["latest_link_time"]
        key["links"] = []
        keys.append(key)

    key_by_id = {key["id"]: key for key in keys}
    for row in conn.execute(
        """
        SELECT
            l.id, l.recall_key_id, l.source_chunk_id, l.relation, l.relation_label,
            l.confidence, l.reason, l.event_time, l.time_label, l.metadata, l.created_at,
            c.raw_input_id, c.text AS source_chunk_text, c.summary AS source_chunk_summary,
            c.spans AS source_chunk_spans, c.source_time AS source_chunk_source_time,
            c.metadata AS source_chunk_metadata
        FROM recall_links l
        JOIN source_chunks c ON c.id = l.source_chunk_id
        ORDER BY COALESCE(l.event_time, l.created_at) DESC
        """
    ):
        link = dict(row)
        link["metadata"] = _json(link.get("metadata"), {})
        link["source_chunk_spans"] = _json(link.get("source_chunk_spans"), [])
        link["source_chunk_metadata"] = _json(link.get("source_chunk_metadata"), {})
        if link["recall_key_id"] in key_by_id:
            key_by_id[link["recall_key_id"]]["links"].append(link)
    return {"total_recall_keys": len(keys), "total_recall_links": sum(key["link_count"] for key in keys), "data": keys}


def _key_from_row(row) -> dict[str, Any]:
    """Decode recall key rows into API-ready dictionaries."""
    return {
        "id": row["id"],
        "name": row["name"],
        "kind": row["kind"],
        "kind_label": row["kind_label"],
        "aliases": _json(row["aliases"], []),
        "summary": row["summary"],
        "metadata": _json(row["metadata"], {}),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _candidate(row, source: str, note: str) -> dict[str, Any]:
    """Attach match details used for ranking and LLM explanation."""
    key = _key_from_row(row)
    key["match_source"] = source
    key["match_notes"] = [note]
    return key


def _save_lookup_rows(conn, key: dict[str, Any]) -> None:
    """Refresh exact and FTS lookup rows for one recall key."""
    key_id = key["id"]
    aliases = [str(alias) for alias in key.get("aliases", []) if str(alias).strip()]
    conn.execute("DELETE FROM recall_key_terms WHERE recall_key_id = ?", (key_id,))
    conn.execute("DELETE FROM recall_keys_fts WHERE recall_key_id = ?", (key_id,))

    # Exact terms are conservative: they prevent obvious duplicates without semantic auto-merging.
    _insert_term(conn, key_id, key["name"], "name")
    for alias in aliases:
        _insert_term(conn, key_id, alias, "alias")

    # FTS gives scalable keyword candidates; source chunks remain the durable evidence.
    conn.execute(
        """
        INSERT INTO recall_keys_fts (recall_key_id, name, aliases, summary, kind_label)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            key_id,
            key["name"],
            " ".join(aliases),
            key.get("summary", ""),
            key.get("kind_label") or "",
        ),
    )


def _insert_term(conn, key_id: str, term: str, term_type: str) -> None:
    """Store one normalized name or alias for exact duplicate checks."""
    normalized = normalize_term(term)
    if not normalized:
        return
    conn.execute(
        """
        INSERT INTO recall_key_terms (recall_key_id, term, normalized_term, term_type)
        VALUES (?, ?, ?, ?)
        """,
        (key_id, term.strip()[:160], normalized, term_type),
    )


def _clean_terms(terms: list[str]) -> list[str]:
    """Dedupe and cap candidate lookup terms."""
    seen = set()
    result = []
    for term in terms:
        clean = str(term).strip()
        lowered = clean.lower()
        if len(clean) >= 3 and lowered not in seen:
            seen.add(lowered)
            result.append(clean)
    return result[:10]


def _normalized_terms(terms: list[str]) -> list[str]:
    """Normalize and dedupe lookup terms."""
    seen = set()
    result = []
    for term in terms:
        normalized = normalize_term(term)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result[:20]


def normalize_term(value: str) -> str:
    """Normalize names and aliases for exact duplicate checks."""
    return " ".join(re.findall(r"[a-z0-9]+", str(value).lower()))


def _fts_query(terms: list[str]) -> str:
    """Build a small OR query for SQLite FTS."""
    words = []
    seen = set()
    for term in terms:
        for word in re.findall(r"[A-Za-z0-9]+", str(term).lower()):
            if len(word) >= 3 and word not in seen:
                seen.add(word)
                words.append(f'"{word}"')
    return " OR ".join(words[:12])


def _merge_candidates(candidates: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """Merge duplicate candidate IDs while keeping all match notes."""
    score = {"exact": 0, "keyword": 1, "vector": 2}
    merged: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        existing = merged.get(candidate["id"])
        if not existing:
            merged[candidate["id"]] = candidate
            continue
        existing["match_notes"] = [*existing.get("match_notes", []), *candidate.get("match_notes", [])]
        if score.get(candidate.get("match_source"), 9) < score.get(existing.get("match_source"), 9):
            existing["match_source"] = candidate.get("match_source")
    return sorted(merged.values(), key=lambda item: score.get(item.get("match_source"), 9))[:limit]


def _json(value: Any, fallback: Any) -> Any:
    try:
        return json.loads(value) if value else fallback
    except (TypeError, json.JSONDecodeError):
        return fallback
