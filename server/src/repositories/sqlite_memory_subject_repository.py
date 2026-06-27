import json
from typing import Any

from kink import inject

from src.infra.sqlite import get_db_connection
from src.repositories.ports.memory_subject_repository import MemorySubjectRepository


@inject
class SqliteMemorySubjectRepository(MemorySubjectRepository):
    def find_candidate_subjects(self, terms: list[str], limit: int = 12) -> list[dict[str, Any]]:
        terms = _clean_terms(terms)
        if not terms:
            return []

        conn = get_db_connection()
        cursor = conn.cursor()
        where = " OR ".join(["(name LIKE ? OR aliases LIKE ? OR summary LIKE ?)"] * len(terms))
        params = []
        for term in terms:
            like = f"%{term}%"
            params.extend([like, like, like])

        cursor.execute(
            f"""
            SELECT id, name, kind, aliases, summary, created_at, updated_at
            FROM memory_subjects
            WHERE {where}
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            [*params, limit],
        )
        return [_subject_from_row(row) for row in cursor.fetchall()]

    def save_subject_index(self, subjects: list[dict[str, Any]], links: list[dict[str, Any]]) -> None:
        if not subjects and not links:
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        for subject in subjects:
            cursor.execute(
                """
                INSERT INTO memory_subjects (id, name, kind, aliases, summary)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    kind = excluded.kind,
                    aliases = excluded.aliases,
                    summary = excluded.summary,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    subject["id"],
                    subject["name"],
                    subject["kind"],
                    json.dumps(subject.get("aliases", []), ensure_ascii=False),
                    subject.get("summary", ""),
                ),
            )

        for link in links:
            cursor.execute(
                """
                INSERT INTO memory_subject_links
                    (id, subject_id, raw_input_id, episode_id, atom_id, relation,
                     confidence, reason, event_time, time_label)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    link["id"],
                    link["subject_id"],
                    link["raw_input_id"],
                    link["episode_id"],
                    link.get("atom_id"),
                    link["relation"],
                    link["confidence"],
                    link.get("reason", ""),
                    link.get("event_time"),
                    link.get("time_label"),
                ),
            )

        conn.commit()

    def get_subject_links(self, subject_ids: list[str], limit: int = 24) -> list[dict[str, Any]]:
        if not subject_ids:
            return []

        conn = get_db_connection()
        cursor = conn.cursor()
        placeholders = ",".join(["?"] * len(subject_ids))
        cursor.execute(
            f"""
            SELECT
                l.id, l.subject_id, l.raw_input_id, l.episode_id, l.atom_id,
                l.relation, l.confidence, l.reason, l.event_time, l.time_label, l.created_at,
                s.name AS subject_name, s.kind AS subject_kind
            FROM memory_subject_links l
            JOIN memory_subjects s ON s.id = l.subject_id
            WHERE l.subject_id IN ({placeholders})
            ORDER BY
                CASE l.relation
                    WHEN 'decision' THEN 0
                    WHEN 'problem' THEN 1
                    WHEN 'status' THEN 2
                    WHEN 'change' THEN 3
                    WHEN 'event' THEN 4
                    ELSE 5
                END,
                COALESCE(l.event_time, l.created_at) DESC,
                l.confidence DESC
            LIMIT ?
            """,
            [*subject_ids, limit],
        )
        return [dict(row) for row in cursor.fetchall()]

    def wipe_subjects(self) -> None:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memory_subject_links")
        cursor.execute("DELETE FROM memory_subjects")
        conn.commit()


def _subject_from_row(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "kind": row["kind"],
        "aliases": json.loads(row["aliases"]) if row["aliases"] else [],
        "summary": row["summary"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _clean_terms(terms: list[str]) -> list[str]:
    seen = set()
    result = []
    for term in terms:
        term = str(term).strip()
        if len(term) < 3 or term.lower() in seen:
            continue
        seen.add(term.lower())
        result.append(term)
    return result[:10]
