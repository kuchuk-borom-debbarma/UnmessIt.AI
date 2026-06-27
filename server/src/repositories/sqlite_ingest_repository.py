import uuid
import json
from src.repositories.ports.ingest_repository import IngestRepository
from src.infra.sqlite import get_db_connection


class SqliteIngestRepository(IngestRepository):
    def save_raw_input(self, job_id: str, raw_content: str) -> str:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        raw_input_id = str(uuid.uuid4())
        
        cursor.execute(
            "INSERT INTO raw_inputs (id, job_id, content) VALUES (?, ?, ?)",
            (raw_input_id, job_id, raw_content)
        )
        conn.commit()
        
        return raw_input_id

    def save_seai(self, episodes: list[dict], atoms: list[dict]) -> None:
        conn = get_db_connection()
        cursor = conn.cursor()

        for episode in episodes:
            cursor.execute(
                """
                INSERT INTO episodes (id, raw_input_id, text, summary, spans)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    episode["id"],
                    episode["raw_input_id"],
                    episode["text"],
                    episode["summary"],
                    json.dumps(episode["spans"], ensure_ascii=False),
                )
            )

        for atom in atoms:
            cursor.execute(
                """
                INSERT INTO atoms
                (id, raw_input_id, episode_id, content, atom_role, annotations, confidence, evidence_spans)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    atom["id"],
                    atom["raw_input_id"],
                    atom["episode_id"],
                    atom["content"],
                    atom["atom_role"],
                    json.dumps(atom["annotations"], ensure_ascii=False),
                    atom["confidence"],
                    json.dumps(atom["evidence_spans"], ensure_ascii=False),
                )
            )

        conn.commit()
