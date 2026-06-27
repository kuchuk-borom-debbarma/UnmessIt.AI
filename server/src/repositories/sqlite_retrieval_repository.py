import json
from typing import List, Dict, Any
from kink import inject
from src.infra.sqlite import get_db_connection
from src.services.retrieval_engine.ports.outbound.RetrievalRepositoryContract import RetrievalRepositoryContract

@inject
class SqliteRetrievalRepositoryImpl(RetrievalRepositoryContract):
    def get_statements_by_ids(self, statement_ids: List[str]) -> List[Dict[str, Any]]:
        if not statement_ids:
            return []
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        placeholders = ','.join(['?'] * len(statement_ids))
        
        query = f"""
            SELECT id, text, type, certainty, notes, source_input_id, parent_id, next_id, level, extra_properties
            FROM memory_items
            WHERE id IN ({placeholders})
        """
        
        cursor.execute(query, statement_ids)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            extra = json.loads(row['extra_properties']) if row['extra_properties'] else {}
            results.append({
                "id": row['id'],
                "text": row['text'],
                "type": row['type'],
                "certainty": row['certainty'],
                "notes": row['notes'],
                "source_input_id": row['source_input_id'],
                "parent_id": row['parent_id'],
                "next_id": row['next_id'],
                "level": row['level'],
                "start_char": extra.get("start_char") or extra.get("start_idx"),
                "end_char": extra.get("end_char") or extra.get("end_idx"),
                "summary": extra.get("summary"),
                "embedding_docs": extra.get("embedding_docs", []),
                "line_number": extra.get("line_number"),
                "raw_text": extra.get("raw_text"),
                "cleaned_text": extra.get("cleaned_text"),
                "evidence_text": extra.get("evidence_text") or extra.get("cleaned_text") or extra.get("raw_text"),
            })
            
        return results

    def get_children_by_parent_ids(self, parent_ids: List[str]) -> List[Dict[str, Any]]:
        if not parent_ids:
            return []

        conn = get_db_connection()
        cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(parent_ids))

        query = f"""
            SELECT id
            FROM memory_items
            WHERE parent_id IN ({placeholders})
            ORDER BY created_at ASC
        """

        cursor.execute(query, parent_ids)
        return self.get_statements_by_ids([row["id"] for row in cursor.fetchall()])

    def get_episodes_by_ids(self, episode_ids: List[str]) -> List[Dict[str, Any]]:
        if not episode_ids:
            return []

        conn = get_db_connection()
        cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(episode_ids))
        cursor.execute(
            f"""
            SELECT e.id, e.raw_input_id, e.text, e.summary, e.spans, e.created_at, r.content AS raw_text
            FROM episodes e
            JOIN raw_inputs r ON r.id = e.raw_input_id
            WHERE e.id IN ({placeholders})
            """,
            episode_ids
        )
        return [self._episode_from_row(row) for row in cursor.fetchall()]

    def get_atoms_by_ids(self, atom_ids: List[str]) -> List[Dict[str, Any]]:
        if not atom_ids:
            return []

        conn = get_db_connection()
        cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(atom_ids))
        cursor.execute(
            f"""
            SELECT a.id, a.raw_input_id, a.episode_id, a.content, a.atom_role, a.annotations,
                   a.confidence, a.evidence_spans, a.created_at, r.content AS raw_text
            FROM atoms a
            JOIN raw_inputs r ON r.id = a.raw_input_id
            WHERE a.id IN ({placeholders})
            """,
            atom_ids
        )
        return [self._atom_from_row(row) for row in cursor.fetchall()]

    def get_atoms_by_episode_ids(self, episode_ids: List[str]) -> List[Dict[str, Any]]:
        if not episode_ids:
            return []

        conn = get_db_connection()
        cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(episode_ids))
        cursor.execute(
            f"""
            SELECT a.id, a.raw_input_id, a.episode_id, a.content, a.atom_role, a.annotations,
                   a.confidence, a.evidence_spans, a.created_at, r.content AS raw_text
            FROM atoms a
            JOIN raw_inputs r ON r.id = a.raw_input_id
            WHERE a.episode_id IN ({placeholders})
            ORDER BY a.created_at ASC
            """,
            episode_ids
        )
        return [self._atom_from_row(row) for row in cursor.fetchall()]

    def search_episodes_by_terms(self, terms: List[str], limit: int = 12) -> List[Dict[str, Any]]:
        terms = _clean_terms(terms)
        if not terms:
            return []

        conn = get_db_connection()
        cursor = conn.cursor()
        where = " OR ".join(["(e.summary LIKE ? OR e.text LIKE ? OR r.content LIKE ?)"] * len(terms))
        params = []
        for term in terms:
            like = f"%{term}%"
            params.extend([like, like, like])
        cursor.execute(
            f"""
            SELECT e.id, e.raw_input_id, e.text, e.summary, e.spans, e.created_at, r.content AS raw_text
            FROM episodes e
            JOIN raw_inputs r ON r.id = e.raw_input_id
            WHERE {where}
            ORDER BY e.created_at DESC
            LIMIT ?
            """,
            [*params, limit],
        )
        return [self._episode_from_row(row) for row in cursor.fetchall()]

    def search_atoms_by_terms(self, terms: List[str], limit: int = 16) -> List[Dict[str, Any]]:
        terms = _clean_terms(terms)
        if not terms:
            return []

        conn = get_db_connection()
        cursor = conn.cursor()
        where = " OR ".join(["(a.content LIKE ? OR a.annotations LIKE ? OR r.content LIKE ?)"] * len(terms))
        params = []
        for term in terms:
            like = f"%{term}%"
            params.extend([like, like, like])
        cursor.execute(
            f"""
            SELECT a.id, a.raw_input_id, a.episode_id, a.content, a.atom_role, a.annotations,
                   a.confidence, a.evidence_spans, a.created_at, r.content AS raw_text
            FROM atoms a
            JOIN raw_inputs r ON r.id = a.raw_input_id
            WHERE {where}
            ORDER BY a.created_at DESC
            LIMIT ?
            """,
            [*params, limit],
        )
        return [self._atom_from_row(row) for row in cursor.fetchall()]

    @staticmethod
    def _episode_from_row(row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "raw_input_id": row["raw_input_id"],
            "text": row["text"],
            "summary": row["summary"],
            "spans": json.loads(row["spans"]) if row["spans"] else [],
            "created_at": row["created_at"],
            "raw_text": row["raw_text"],
        }

    @staticmethod
    def _atom_from_row(row) -> Dict[str, Any]:
        evidence_spans = json.loads(row["evidence_spans"]) if row["evidence_spans"] else []
        raw_text = row["raw_text"] or ""
        return {
            "id": row["id"],
            "raw_input_id": row["raw_input_id"],
            "episode_id": row["episode_id"],
            "content": row["content"],
            "atom_role": row["atom_role"],
            "annotations": json.loads(row["annotations"]) if row["annotations"] else [],
            "confidence": row["confidence"],
            "evidence_spans": evidence_spans,
            "evidence_text": "\n...\n".join(raw_text[span["start"]:span["end"]] for span in evidence_spans),
            "created_at": row["created_at"],
            "raw_text": raw_text,
        }


def _clean_terms(terms: List[str]) -> List[str]:
    seen = set()
    result = []
    for term in terms:
        term = str(term).strip()
        if len(term) < 3 or term.lower() in seen:
            continue
        seen.add(term.lower())
        result.append(term)
    return result[:8]
