from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from src.infra.sqlite import get_connection

logger = logging.getLogger(__name__)


def list_for_user(user_id: str) -> list[dict[str, Any]]:
    """Return all config presets for a user."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM user_config_presets WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    ).fetchall()
    return [dict(row) for row in rows]


def get_active(user_id: str) -> dict[str, Any] | None:
    """Return the currently active config preset for a user."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM user_config_presets WHERE user_id = ? AND is_active = 1",
        (user_id,)
    ).fetchone()
    return dict(row) if row else None


def get_by_id(preset_id: str, user_id: str) -> dict[str, Any] | None:
    """Return a specific config preset."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM user_config_presets WHERE id = ? AND user_id = ?",
        (preset_id, user_id)
    ).fetchone()
    return dict(row) if row else None


def save(preset: dict[str, Any], user_id: str) -> str:
    """Create or update a preset."""
    preset_id = preset.get("id") or str(uuid4())
    conn = get_connection()
    
    # Check if this is the first preset; if so, make it active
    if not preset.get("id"):
        count = conn.execute("SELECT COUNT(*) FROM user_config_presets WHERE user_id = ?", (user_id,)).fetchone()[0]
        is_active = 1 if count == 0 else preset.get("is_active", 0)
    else:
        is_active = preset.get("is_active", 0)
        
    if is_active:
        conn.execute("UPDATE user_config_presets SET is_active = 0 WHERE user_id = ?", (user_id,))
        
    conn.execute(
        """
        INSERT INTO user_config_presets (
            id, user_id, name, is_active,
            llm_provider, llm_model, llm_base_url, llm_api_key, llm_temperature, llm_max_retries, llm_max_tokens,
            embedding_provider, embedding_model, embedding_base_url, embedding_api_key,
            llm_rate_limit_per_minute, embedding_rate_limit_per_minute,
            chunk_size, chunk_overlap, ingest_retry_backoff_seconds
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            is_active=excluded.is_active,
            llm_provider=excluded.llm_provider,
            llm_model=excluded.llm_model,
            llm_base_url=excluded.llm_base_url,
            llm_api_key=excluded.llm_api_key,
            llm_temperature=excluded.llm_temperature,
            llm_max_retries=excluded.llm_max_retries,
            llm_max_tokens=excluded.llm_max_tokens,
            embedding_provider=excluded.embedding_provider,
            embedding_model=excluded.embedding_model,
            embedding_base_url=excluded.embedding_base_url,
            embedding_api_key=excluded.embedding_api_key,
            llm_rate_limit_per_minute=excluded.llm_rate_limit_per_minute,
            embedding_rate_limit_per_minute=excluded.embedding_rate_limit_per_minute,
            chunk_size=excluded.chunk_size,
            chunk_overlap=excluded.chunk_overlap,
            ingest_retry_backoff_seconds=excluded.ingest_retry_backoff_seconds,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            preset_id,
            user_id,
            preset.get("name", "Default"),
            is_active,
            preset.get("llm_provider", "openai").lower(),
            preset.get("llm_model", "gpt-4o"),
            preset.get("llm_base_url"),
            preset.get("llm_api_key", ""),
            float(preset.get("llm_temperature", 0.0)),
            int(preset.get("llm_max_retries", 2)),
            int(preset.get("llm_max_tokens", 2048)),
            preset.get("embedding_provider", "openai").lower(),
            preset.get("embedding_model", "text-embedding-3-small"),
            preset.get("embedding_base_url"),
            preset.get("embedding_api_key", ""),
            int(preset.get("llm_rate_limit_per_minute", 0)),
            int(preset.get("embedding_rate_limit_per_minute", 0)),
            int(preset.get("chunk_size", 1000)),
            int(preset.get("chunk_overlap", 200)),
            preset.get("ingest_retry_backoff_seconds", "5,15,30,60,120"),
        ),
    )
    conn.commit()
    
    from src.infra.settings import get_user_settings
    get_user_settings.cache_clear()
    return preset_id


def set_active(preset_id: str, user_id: str) -> bool:
    """Set a preset as active, deactivating others for this user."""
    conn = get_connection()
    row = conn.execute("SELECT id FROM user_config_presets WHERE id = ? AND user_id = ?", (preset_id, user_id)).fetchone()
    if not row:
        return False
        
    conn.execute("UPDATE user_config_presets SET is_active = 0 WHERE user_id = ?", (user_id,))
    conn.execute("UPDATE user_config_presets SET is_active = 1 WHERE id = ?", (preset_id,))
    conn.commit()
    from src.infra.settings import get_user_settings
    get_user_settings.cache_clear()
    return True


def delete(preset_id: str, user_id: str) -> bool:
    """Delete a preset. If it was active, activate the most recently created one."""
    conn = get_connection()
    row = conn.execute("SELECT is_active FROM user_config_presets WHERE id = ? AND user_id = ?", (preset_id, user_id)).fetchone()
    if not row:
        return False
        
    conn.execute("DELETE FROM user_config_presets WHERE id = ?", (preset_id,))
    
    if row["is_active"]:
        next_preset = conn.execute("SELECT id FROM user_config_presets WHERE user_id = ? ORDER BY created_at DESC LIMIT 1", (user_id,)).fetchone()
        if next_preset:
            conn.execute("UPDATE user_config_presets SET is_active = 1 WHERE id = ?", (next_preset["id"],))
            
    conn.commit()
    from src.infra.settings import get_user_settings
    get_user_settings.cache_clear()
    return True
