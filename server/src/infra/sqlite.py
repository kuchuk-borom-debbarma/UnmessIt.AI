from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = SERVER_DIR / "data"
RESOURCES_DIR = SERVER_DIR / "resources"
DEFAULT_DB_PATH = DATA_DIR / "sqlite.db"

_local = threading.local()


def get_connection(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Return this thread's SQLite connection, creating it on first use.

    Each thread in the asyncio thread pool executor gets its own connection.
    WAL mode (set once at init_db time) handles concurrent multi-connection
    access safely at the SQLite level.
    """
    conn = getattr(_local, "connection", None)
    if conn is not None:
        return conn

    os.makedirs(Path(db_path).parent, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    _local.connection = conn
    return conn


def init_db() -> None:
    """Apply the checked-in schema at app startup."""
    schema_path = RESOURCES_DIR / "schema.sql"
    conn = get_connection()
    conn.executescript(schema_path.read_text())
    _migrate_ingest_job_status(conn)
    _ensure_unique_ingest_content_hash(conn)
    _add_column_if_missing(conn, "raw_inputs", "content_hash", "TEXT")
    _add_column_if_missing(conn, "raw_inputs", "user_id", "TEXT REFERENCES users(id) ON DELETE CASCADE")
    _add_column_if_missing(conn, "recall_keys", "user_id", "TEXT REFERENCES users(id) ON DELETE CASCADE")
    _add_column_if_missing(conn, "source_chunks", "user_id", "TEXT REFERENCES users(id) ON DELETE CASCADE")
    _add_column_if_missing(conn, "recall_links", "user_id", "TEXT REFERENCES users(id) ON DELETE CASCADE")
    _add_column_if_missing(conn, "notes", "deleted_at", "DATETIME")
    _add_column_if_missing(conn, "notes", "directory_id", "TEXT REFERENCES directories(id) ON DELETE SET NULL")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_inputs_job_id ON raw_inputs(job_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_inputs_content_hash ON raw_inputs(content_hash)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_inputs_user_id ON raw_inputs(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source_chunks_user_id ON source_chunks(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_recall_keys_user_id ON recall_keys(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_recall_links_user_id ON recall_links(user_id)")
    _add_column_if_missing(conn, "user_config_presets", "llm_rate_limit_per_minute", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(conn, "user_config_presets", "embedding_rate_limit_per_minute", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(conn, "user_config_presets", "embedding_batch_size", "INTEGER NOT NULL DEFAULT 100")
    _add_column_if_missing(conn, "user_config_presets", "ingest_retry_backoff_seconds", "TEXT NOT NULL DEFAULT '5,15,30,60,120'")
    _add_column_if_missing(conn, "source_chunks", "directory_path", "TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_directories_user_name ON directories(user_id, name)")
    conn.commit()


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    """SQLite cannot add columns with `IF NOT EXISTS`, so migrations check first."""
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _ensure_unique_ingest_content_hash(conn: sqlite3.Connection) -> None:
    """Durability reuses one job per exact input hash; enforce that invariant."""
    duplicates = conn.execute(
        "SELECT 1 FROM ingest_jobs GROUP BY content_hash HAVING COUNT(*) > 1 LIMIT 1"
    ).fetchone()
    if duplicates:
        return
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = 'idx_ingest_jobs_content_hash'"
    ).fetchone()
    if row and str(row["sql"] or "").upper().startswith("CREATE UNIQUE INDEX"):
        return
    conn.execute("DROP INDEX IF EXISTS idx_ingest_jobs_content_hash")
    conn.execute("CREATE UNIQUE INDEX idx_ingest_jobs_content_hash ON ingest_jobs(content_hash)")


def _migrate_ingest_job_status(conn: sqlite3.Connection) -> None:
    """Rebuild old durability tables so `aborted` and `paused` are allowed states."""
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'ingest_jobs'").fetchone()
    if not row or "'paused'" in row["sql"]:
        return

    # SQLite cannot alter CHECK constraints, so this one migration rebuilds the
    # two durability tables that reference each other.
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("ALTER TABLE ingest_checkpoints RENAME TO ingest_checkpoints_old")
    conn.execute("ALTER TABLE ingest_jobs RENAME TO ingest_jobs_old")
    conn.execute("DROP INDEX IF EXISTS idx_ingest_jobs_content_hash")
    conn.execute("DROP INDEX IF EXISTS idx_ingest_jobs_status_next_run")
    conn.execute("DROP INDEX IF EXISTS idx_ingest_checkpoints_job_stage")
    conn.executescript(
        """
        CREATE TABLE ingest_jobs (
            id TEXT PRIMARY KEY,
            content_hash TEXT NOT NULL,
            raw_input_id TEXT,
            status TEXT NOT NULL CHECK(status IN ('queued', 'running', 'waiting_retry', 'complete', 'failed', 'aborted', 'paused')),
            stage TEXT NOT NULL,
            attempt_count INTEGER NOT NULL DEFAULT 0,
            next_run_at DATETIME,
            error TEXT,
            metadata JSON NOT NULL DEFAULT '{}',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(raw_input_id) REFERENCES raw_inputs(id) ON DELETE SET NULL
        );
        CREATE UNIQUE INDEX idx_ingest_jobs_content_hash ON ingest_jobs(content_hash);
        CREATE INDEX idx_ingest_jobs_status_next_run ON ingest_jobs(status, next_run_at);

        CREATE TABLE ingest_checkpoints (
            job_id TEXT NOT NULL,
            stage TEXT NOT NULL,
            unit_key TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('running', 'complete', 'failed')),
            output_ref TEXT,
            error TEXT,
            metadata JSON NOT NULL DEFAULT '{}',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(job_id, stage, unit_key),
            FOREIGN KEY(job_id) REFERENCES ingest_jobs(id) ON DELETE CASCADE
        );
        CREATE INDEX idx_ingest_checkpoints_job_stage ON ingest_checkpoints(job_id, stage, status);
        """
    )
    conn.execute(
        """
        INSERT INTO ingest_jobs
            (id, content_hash, raw_input_id, status, stage, attempt_count, next_run_at, error, metadata, created_at, updated_at)
        SELECT id, content_hash, raw_input_id, status, stage, attempt_count, next_run_at, error, metadata, created_at, updated_at
        FROM ingest_jobs_old
        """
    )
    conn.execute(
        """
        INSERT INTO ingest_checkpoints
            (job_id, stage, unit_key, status, output_ref, error, metadata, created_at, updated_at)
        SELECT job_id, stage, unit_key, status, output_ref, error, metadata, created_at, updated_at
        FROM ingest_checkpoints_old
        """
    )
    conn.execute("DROP TABLE ingest_checkpoints_old")
    conn.execute("DROP TABLE ingest_jobs_old")
    conn.execute("PRAGMA foreign_keys = ON")
