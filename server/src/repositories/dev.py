from __future__ import annotations

from src.infra.sqlite import get_connection
from src.repositories import recall, raw_inputs, retrieval_index, source_chunk_vectors, source_chunks


def memory_view(user_id: str | None = None) -> dict:
    """Return raw inputs and chunks for the dev inspector."""
    return source_chunks.list_with_raw_inputs(user_id)


def raw_input(input_id: str) -> dict | None:
    """Return one raw source document for the dev inspector."""
    return raw_inputs.get(input_id)


def recall_view(user_id: str | None = None) -> dict:
    """Return recall keys and links for the dev inspector."""
    return recall.get_view(user_id)


def wipe_all() -> None:
    """Delete all active local memory data.

    The app is local-first/dev right now, so a hard wipe is simpler than
    lifecycle states or tombstones.
    """
    user_ids = raw_inputs.list_user_ids()
    conn = get_connection()
    conn.execute("DELETE FROM ingest_checkpoints")
    conn.execute("DELETE FROM ingest_jobs")
    conn.execute("DELETE FROM recall_links")
    # FTS tables do not receive foreign-key cascades from recall_keys.
    conn.execute("DELETE FROM recall_keys_fts")
    conn.execute("DELETE FROM recall_key_terms")
    conn.execute("DELETE FROM recall_keys")
    conn.execute("DELETE FROM source_chunks")
    conn.execute("DELETE FROM raw_inputs")
    for user_id in user_ids:
        retrieval_index.bump(user_id, conn)
    conn.commit()
    for user_id in user_ids:
        source_chunk_vectors.reset(user_id)
