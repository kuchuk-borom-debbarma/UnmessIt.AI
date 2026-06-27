import json

from src.infra.sqlite import get_db_connection


class SqliteDevRepository:
    def get_facts(self) -> list[dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, text, type, certainty, notes, source_input_id, parent_id,
                   next_id, level, extra_properties, created_at
            FROM memory_items
            ORDER BY created_at DESC
        """)

        facts = []
        for row in cursor.fetchall():
            extra = json.loads(row["extra_properties"]) if row["extra_properties"] else {}
            facts.append({
                "id": row["id"],
                "text": row["text"],
                "type": row["type"],
                "certainty": row["certainty"],
                "notes": row["notes"],
                "source_input_id": row["source_input_id"],
                "raw_input_url": f"/dev/raw_inputs/{row['source_input_id']}" if row["source_input_id"] else None,
                "parent_id": row["parent_id"],
                "next_id": row["next_id"],
                "level": row["level"],
                "topics": extra.get("topics", []),
                "entities": extra.get("entities", []),
                "summary_text": extra.get("summary", row["text"]),
                "start_idx": extra.get("start_idx"),
                "end_idx": extra.get("end_idx"),
                "embedding_docs": extra.get("embedding_docs", []),
                "evidence_text": extra.get("evidence_text", ""),
                "cleaned_text": extra.get("cleaned_text", ""),
                "raw_text": extra.get("raw_text", ""),
                "created_at": row["created_at"],
            })
        return facts

    def get_seai(self) -> dict:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, job_id, content, created_at FROM raw_inputs ORDER BY created_at DESC")
        raw_inputs = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT id, raw_input_id, text, summary, spans, created_at FROM episodes ORDER BY created_at ASC")
        episodes = []
        for row in cursor.fetchall():
            episode = dict(row)
            episode["spans"] = json.loads(episode["spans"]) if episode["spans"] else []
            episode["atoms"] = []
            episodes.append(episode)

        cursor.execute("""
            SELECT id, raw_input_id, episode_id, content, atom_role, annotations,
                   confidence, evidence_spans, created_at
            FROM atoms
            ORDER BY created_at ASC
        """)
        atoms = []
        for row in cursor.fetchall():
            atom = dict(row)
            atom["annotations"] = json.loads(atom["annotations"]) if atom["annotations"] else []
            atom["evidence_spans"] = json.loads(atom["evidence_spans"]) if atom["evidence_spans"] else []
            atoms.append(atom)

        episodes_by_id = {episode["id"]: episode for episode in episodes}
        episodes_by_raw = {}
        for episode in episodes:
            episodes_by_raw.setdefault(episode["raw_input_id"], []).append(episode)
        for atom in atoms:
            if atom["episode_id"] in episodes_by_id:
                episodes_by_id[atom["episode_id"]]["atoms"].append(atom)

        for raw in raw_inputs:
            raw["episodes"] = episodes_by_raw.get(raw["id"], [])

        return {
            "total_raw_inputs": len(raw_inputs),
            "total_episodes": len(episodes),
            "total_atoms": len(atoms),
            "data": raw_inputs,
        }

    def get_raw_input(self, input_id: str) -> dict | None:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM raw_inputs WHERE id = ?", (input_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {"id": input_id, "content": row["content"]}

    def get_subjects(self) -> dict:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                s.id, s.name, s.kind, s.aliases, s.summary, s.created_at, s.updated_at,
                COUNT(l.id) AS link_count,
                MAX(COALESCE(l.event_time, l.created_at)) AS latest_link_time
            FROM memory_subjects s
            LEFT JOIN memory_subject_links l ON l.subject_id = s.id
            GROUP BY s.id
            ORDER BY latest_link_time DESC, s.updated_at DESC
        """)
        subjects = []
        for row in cursor.fetchall():
            subject = dict(row)
            subject["aliases"] = json.loads(subject["aliases"]) if subject["aliases"] else []
            subject["links"] = []
            subjects.append(subject)

        subject_by_id = {subject["id"]: subject for subject in subjects}
        cursor.execute("""
            SELECT
                l.id, l.subject_id, l.raw_input_id, l.episode_id, l.atom_id,
                l.relation, l.confidence, l.reason, l.event_time, l.time_label, l.created_at,
                e.summary AS episode_summary,
                a.content AS atom_content
            FROM memory_subject_links l
            JOIN episodes e ON e.id = l.episode_id
            LEFT JOIN atoms a ON a.id = l.atom_id
            ORDER BY COALESCE(l.event_time, l.created_at) DESC
        """)
        for row in cursor.fetchall():
            link = dict(row)
            subject = subject_by_id.get(link["subject_id"])
            if subject:
                subject["links"].append(link)

        return {
            "total_subjects": len(subjects),
            "total_links": sum(subject["link_count"] for subject in subjects),
            "data": subjects,
        }

    def wipe_all(self) -> None:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memory_subject_links")
        cursor.execute("DELETE FROM memory_subjects")
        cursor.execute("DELETE FROM atoms")
        cursor.execute("DELETE FROM episodes")
        cursor.execute("DELETE FROM memory_items")
        cursor.execute("DELETE FROM raw_inputs")
        # ponytail: old DB files may still have these legacy tables.
        for table in ("memory_item_placements", "hierarchy_relations", "view_nodes", "hierarchy_change_log"):
            try:
                cursor.execute(f"DELETE FROM {table}")
            except Exception:
                pass
        conn.commit()
