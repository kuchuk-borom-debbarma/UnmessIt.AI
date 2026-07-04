from __future__ import annotations

from src.infra.sqlite import get_connection


def get_version(user_id: str) -> int:
    """Return the user's retrieval index version, defaulting to 0."""
    row = get_connection().execute(
        "SELECT version FROM user_retrieval_index_versions WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    return int(row["version"]) if row else 0


def bump(user_id: str | None, conn=None) -> int:
    """Invalidate exact evidence caches for one user's retrieval index."""
    if not user_id:
        return 0
    db = conn or get_connection()
    db.execute(
        """
        INSERT INTO user_retrieval_index_versions (user_id, version)
        VALUES (?, 1)
        ON CONFLICT(user_id) DO UPDATE SET
            version = version + 1,
            updated_at = CURRENT_TIMESTAMP
        """,
        (user_id,),
    )
    if conn is None:
        db.commit()
        return get_version(user_id)
    row = db.execute(
        "SELECT version FROM user_retrieval_index_versions WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    return int(row["version"]) if row else 0
