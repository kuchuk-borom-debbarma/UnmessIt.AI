from __future__ import annotations

import logging
import json
from typing import Any
from uuid import uuid4

from src.infra.sqlite import get_connection

logger = logging.getLogger(__name__)

PROCESSING_DEFAULTS = {
    "embedding_provider": "openai",
    "embedding_model": "text-embedding-3-small",
    "embedding_batch_size": 100,
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "ingest_retry_backoff_seconds": "5,15,30,60,120",
}


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


def get_processing(user_id: str) -> dict[str, Any]:
    """Return stable ingest/retrieval settings, seeding from the active legacy preset."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM user_processing_settings WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if row:
        return dict(row)

    active = get_active(user_id) or {}
    processing = {
        **PROCESSING_DEFAULTS,
        **{key: active[key] for key in PROCESSING_DEFAULTS if key in active and active[key] is not None},
    }
    save_processing(processing, user_id)
    return get_processing(user_id)


def save_processing(settings: dict[str, Any], user_id: str) -> None:
    """Save stable processing settings that do not rotate mid-job."""
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO user_processing_settings (
            user_id, embedding_provider, embedding_model, embedding_batch_size,
            chunk_size, chunk_overlap, ingest_retry_backoff_seconds
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            embedding_provider=excluded.embedding_provider,
            embedding_model=excluded.embedding_model,
            embedding_batch_size=excluded.embedding_batch_size,
            chunk_size=excluded.chunk_size,
            chunk_overlap=excluded.chunk_overlap,
            ingest_retry_backoff_seconds=excluded.ingest_retry_backoff_seconds,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            user_id,
            settings.get("embedding_provider", PROCESSING_DEFAULTS["embedding_provider"]).lower(),
            settings.get("embedding_model", PROCESSING_DEFAULTS["embedding_model"]),
            int(settings.get("embedding_batch_size", PROCESSING_DEFAULTS["embedding_batch_size"])),
            int(settings.get("chunk_size", PROCESSING_DEFAULTS["chunk_size"])),
            int(settings.get("chunk_overlap", PROCESSING_DEFAULTS["chunk_overlap"])),
            settings.get("ingest_retry_backoff_seconds", PROCESSING_DEFAULTS["ingest_retry_backoff_seconds"]),
        ),
    )
    conn.commit()
    _clear_settings_cache()


def get_rotation_config(user_id: str) -> dict[str, Any]:
    """Return the ordered rotation config for a user."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM user_rotation_config WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if not row:
        return {"user_id": user_id, "enabled": 0, "preset_ids": []}
    config = dict(row)
    config["preset_ids"] = _json_list(config.get("preset_ids"))
    return config


def save_rotation_config(user_id: str, enabled: bool, preset_ids: list[str]) -> dict[str, Any]:
    """Save per-job rotation order without a persistent pointer."""
    clean_ids = _owned_ordered_ids(user_id, preset_ids)
    if enabled and len(clean_ids) < 2:
        raise ValueError("Rotation needs at least two presets.")
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO user_rotation_config (user_id, enabled, preset_ids)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            enabled=excluded.enabled,
            preset_ids=excluded.preset_ids,
            updated_at=CURRENT_TIMESTAMP
        """,
        (user_id, 1 if enabled else 0, json.dumps(clean_ids, ensure_ascii=False)),
    )
    conn.commit()
    _clear_settings_cache()
    return get_rotation_config(user_id)


def rotation_candidates(user_id: str) -> list[dict[str, Any]]:
    """Return the preset lanes to try for one job/request."""
    config = get_rotation_config(user_id)
    if config.get("enabled"):
        return [preset for preset in _presets_by_order(user_id, config.get("preset_ids", [])) if preset]
    active = get_active(user_id)
    return [active] if active else []


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
            llm_rate_limit_per_minute, embedding_rate_limit_per_minute, embedding_batch_size,
            chunk_size, chunk_overlap, ingest_retry_backoff_seconds
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            embedding_batch_size=excluded.embedding_batch_size,
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
            int(preset.get("embedding_batch_size", 100)),
            int(preset.get("chunk_size", 1000)),
            int(preset.get("chunk_overlap", 200)),
            preset.get("ingest_retry_backoff_seconds", "5,15,30,60,120"),
        ),
    )
    conn.commit()
    
    _clear_settings_cache()
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
    _clear_settings_cache()
    return True


def delete(preset_id: str, user_id: str) -> bool:
    """Delete a preset. If it was active, activate the most recently created one."""
    conn = get_connection()
    row = conn.execute("SELECT is_active FROM user_config_presets WHERE id = ? AND user_id = ?", (preset_id, user_id)).fetchone()
    if not row:
        return False
        
    conn.execute("DELETE FROM user_config_presets WHERE id = ?", (preset_id,))
    config = get_rotation_config(user_id)
    if preset_id in config.get("preset_ids", []):
        remaining = [item for item in config["preset_ids"] if item != preset_id]
        conn.execute(
            """
            INSERT INTO user_rotation_config (user_id, enabled, preset_ids)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                enabled=excluded.enabled,
                preset_ids=excluded.preset_ids,
                updated_at=CURRENT_TIMESTAMP
            """,
            (user_id, 1 if config.get("enabled") and len(remaining) >= 2 else 0, json.dumps(remaining, ensure_ascii=False)),
        )
    
    if row["is_active"]:
        next_preset = conn.execute("SELECT id FROM user_config_presets WHERE user_id = ? ORDER BY created_at DESC LIMIT 1", (user_id,)).fetchone()
        if next_preset:
            conn.execute("UPDATE user_config_presets SET is_active = 1 WHERE id = ?", (next_preset["id"],))
            
    conn.commit()
    _clear_settings_cache()
    return True


def _presets_by_order(user_id: str, preset_ids: list[str]) -> list[dict[str, Any]]:
    if not preset_ids:
        return []
    by_id = {preset["id"]: preset for preset in list_for_user(user_id)}
    return [by_id[preset_id] for preset_id in preset_ids if preset_id in by_id]


def _owned_ordered_ids(user_id: str, preset_ids: list[str]) -> list[str]:
    owned = {preset["id"] for preset in list_for_user(user_id)}
    clean: list[str] = []
    for preset_id in preset_ids:
        if preset_id in owned and preset_id not in clean:
            clean.append(preset_id)
    return clean


def _json_list(value: Any) -> list[str]:
    try:
        items = json.loads(value) if isinstance(value, str) else value
    except json.JSONDecodeError:
        items = []
    return [str(item) for item in items] if isinstance(items, list) else []


def _clear_settings_cache() -> None:
    from src.infra.settings import get_user_settings, get_user_setting_candidates

    get_user_settings.cache_clear()
    get_user_setting_candidates.cache_clear()
