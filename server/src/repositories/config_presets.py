from __future__ import annotations

import logging
import json
from typing import Any
from uuid import uuid4

from src.infra.sqlite import get_connection

logger = logging.getLogger(__name__)

PROCESSING_DEFAULTS = {
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
            "openai",
            "text-embedding-3-small",
            int(settings.get("embedding_batch_size", PROCESSING_DEFAULTS["embedding_batch_size"])),
            int(settings.get("chunk_size", PROCESSING_DEFAULTS["chunk_size"])),
            int(settings.get("chunk_overlap", PROCESSING_DEFAULTS["chunk_overlap"])),
            settings.get("ingest_retry_backoff_seconds", PROCESSING_DEFAULTS["ingest_retry_backoff_seconds"]),
        ),
    )
    conn.commit()
    _clear_settings_cache()


def get_rotation_config(user_id: str) -> dict[str, Any]:
    """Return independent LLM and embedding rotation config for a user."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM user_rotation_config WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    active = get_active(user_id) or {}
    active_id = active.get("id")
    if not row:
        return _rotation_config_response(user_id, {}, active_id)
    config = dict(row)
    return _rotation_config_response(user_id, config, active_id)


def save_rotation_config(user_id: str, enabled: bool, preset_ids: list[str]) -> dict[str, Any]:
    """Save legacy rotation order to both LLM and embedding lanes."""
    clean_ids = _owned_ordered_ids(user_id, preset_ids)
    if enabled and len(clean_ids) < 2:
        raise ValueError("Rotation needs at least two presets.")
    active_id = (get_active(user_id) or {}).get("id")
    return save_split_rotation_config(
        user_id,
        llm_enabled=enabled,
        llm_preset_ids=clean_ids,
        embedding_enabled=enabled,
        embedding_preset_ids=clean_ids,
        llm_active_preset_id=active_id,
        embedding_active_preset_id=active_id,
    )


def save_split_rotation_config(
    user_id: str,
    *,
    llm_enabled: bool,
    llm_preset_ids: list[str],
    embedding_enabled: bool,
    embedding_preset_ids: list[str],
    llm_active_preset_id: str | None = None,
    embedding_active_preset_id: str | None = None,
) -> dict[str, Any]:
    """Save independent LLM and embedding lane modes."""
    llm_ids = _owned_ordered_ids(user_id, llm_preset_ids)
    embedding_ids = _owned_ordered_ids(user_id, embedding_preset_ids)
    if llm_enabled and len(llm_ids) < 2:
        raise ValueError("LLM rotation needs at least two presets.")
    if embedding_enabled and len(embedding_ids) < 2:
        raise ValueError("Embedding rotation needs at least two presets.")

    active_id = (get_active(user_id) or {}).get("id")
    llm_active = _owned_active_id(user_id, llm_active_preset_id) or active_id
    embedding_active = _owned_active_id(user_id, embedding_active_preset_id) or active_id
    legacy_enabled = bool(llm_enabled and embedding_enabled and llm_ids == embedding_ids)
    legacy_ids = llm_ids if legacy_enabled else []
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO user_rotation_config (
            user_id, enabled, preset_ids,
            llm_enabled, llm_preset_ids, llm_active_preset_id,
            embedding_enabled, embedding_preset_ids, embedding_active_preset_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            enabled=excluded.enabled,
            preset_ids=excluded.preset_ids,
            llm_enabled=excluded.llm_enabled,
            llm_preset_ids=excluded.llm_preset_ids,
            llm_active_preset_id=excluded.llm_active_preset_id,
            embedding_enabled=excluded.embedding_enabled,
            embedding_preset_ids=excluded.embedding_preset_ids,
            embedding_active_preset_id=excluded.embedding_active_preset_id,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            user_id,
            1 if legacy_enabled else 0,
            json.dumps(legacy_ids, ensure_ascii=False),
            1 if llm_enabled else 0,
            json.dumps(llm_ids, ensure_ascii=False),
            llm_active,
            1 if embedding_enabled else 0,
            json.dumps(embedding_ids, ensure_ascii=False),
            embedding_active,
        ),
    )
    conn.commit()
    _clear_settings_cache()
    return get_rotation_config(user_id)


def save_lane_rotation_config(user_id: str, lane: str, enabled: bool, preset_ids: list[str], active_preset_id: str | None = None) -> dict[str, Any]:
    """Save one lane while preserving the other lane."""
    config = get_rotation_config(user_id)
    llm = config["llm"]
    embedding = config["embedding"]
    if lane == "llm":
        llm = {"enabled": enabled, "preset_ids": preset_ids, "active_preset_id": active_preset_id or llm.get("active_preset_id")}
    elif lane == "embedding":
        embedding = {"enabled": enabled, "preset_ids": preset_ids, "active_preset_id": active_preset_id or embedding.get("active_preset_id")}
    else:
        raise ValueError("Lane must be llm or embedding.")
    return save_split_rotation_config(
        user_id,
        llm_enabled=bool(llm.get("enabled")),
        llm_preset_ids=llm.get("preset_ids", []),
        embedding_enabled=bool(embedding.get("enabled")),
        embedding_preset_ids=embedding.get("preset_ids", []),
        llm_active_preset_id=llm.get("active_preset_id"),
        embedding_active_preset_id=embedding.get("active_preset_id"),
    )


def rotation_candidates(user_id: str) -> list[dict[str, Any]]:
    """Return LLM preset lanes to try for one job/request."""
    return llm_rotation_candidates(user_id)


def llm_rotation_candidates(user_id: str) -> list[dict[str, Any]]:
    """Return LLM preset lanes to try for one job/request."""
    return _lane_candidates(user_id, "llm")


def embedding_rotation_candidates(user_id: str) -> list[dict[str, Any]]:
    """Return embedding preset lanes to try for one job/request."""
    return _lane_candidates(user_id, "embedding")


def _lane_candidates(user_id: str, lane: str) -> list[dict[str, Any]]:
    config = get_rotation_config(user_id)
    lane_config = config[lane]
    if lane_config.get("enabled"):
        return [preset for preset in _presets_by_order(user_id, lane_config.get("preset_ids", [])) if preset]
    preset = get_by_id(str(lane_config.get("active_preset_id") or ""), user_id)
    if preset:
        return [preset]
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
            int(preset["llm_max_tokens"]) if preset.get("llm_max_tokens") is not None else None,
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
    _mirror_split_configs(preset_id, preset, user_id)
    
    _clear_settings_cache()
    return preset_id


def set_active(preset_id: str, user_id: str) -> bool:
    """Set a preset as active for both lanes, deactivating rotations."""
    conn = get_connection()
    row = conn.execute("SELECT id FROM user_config_presets WHERE id = ? AND user_id = ?", (preset_id, user_id)).fetchone()
    if not row:
        return False
        
    conn.execute("UPDATE user_config_presets SET is_active = 0 WHERE user_id = ?", (user_id,))
    conn.execute("UPDATE user_config_presets SET is_active = 1 WHERE id = ?", (preset_id,))
    conn.execute(
        """
        INSERT INTO user_rotation_config (
            user_id, enabled, preset_ids,
            llm_enabled, llm_preset_ids, llm_active_preset_id,
            embedding_enabled, embedding_preset_ids, embedding_active_preset_id
        )
        VALUES (
            ?, 0, COALESCE((SELECT preset_ids FROM user_rotation_config WHERE user_id = ?), '[]'),
            0, COALESCE((SELECT llm_preset_ids FROM user_rotation_config WHERE user_id = ?), '[]'), ?,
            0, COALESCE((SELECT embedding_preset_ids FROM user_rotation_config WHERE user_id = ?), '[]'), ?
        )
        ON CONFLICT(user_id) DO UPDATE SET
            enabled=0,
            llm_enabled=0,
            llm_active_preset_id=excluded.llm_active_preset_id,
            embedding_enabled=0,
            embedding_active_preset_id=excluded.embedding_active_preset_id,
            updated_at=CURRENT_TIMESTAMP
        """,
        (user_id, user_id, user_id, preset_id, user_id, preset_id),
    )
    conn.commit()
    _clear_settings_cache()
    return True


def set_active_lane(preset_id: str, user_id: str, lane: str) -> bool:
    """Set a preset as active for one lane and disable that lane's rotation."""
    if lane not in {"llm", "embedding"}:
        raise ValueError("Lane must be llm or embedding.")
    conn = get_connection()
    row = conn.execute("SELECT id FROM user_config_presets WHERE id = ? AND user_id = ?", (preset_id, user_id)).fetchone()
    if not row:
        return False
    config = get_rotation_config(user_id)
    other = "embedding" if lane == "llm" else "llm"
    lane_config = {"enabled": False, "preset_ids": config[lane].get("preset_ids", []), "active_preset_id": preset_id}
    other_config = config[other]
    save_split_rotation_config(
        user_id,
        llm_enabled=bool(lane_config["enabled"] if lane == "llm" else other_config.get("enabled")),
        llm_preset_ids=lane_config["preset_ids"] if lane == "llm" else other_config.get("preset_ids", []),
        embedding_enabled=bool(lane_config["enabled"] if lane == "embedding" else other_config.get("enabled")),
        embedding_preset_ids=lane_config["preset_ids"] if lane == "embedding" else other_config.get("preset_ids", []),
        llm_active_preset_id=lane_config["active_preset_id"] if lane == "llm" else other_config.get("active_preset_id"),
        embedding_active_preset_id=lane_config["active_preset_id"] if lane == "embedding" else other_config.get("active_preset_id"),
    )
    return True


def delete(preset_id: str, user_id: str) -> bool:
    """Delete a preset. If it was active, activate the most recently created one."""
    conn = get_connection()
    row = conn.execute("SELECT is_active FROM user_config_presets WHERE id = ? AND user_id = ?", (preset_id, user_id)).fetchone()
    if not row:
        return False
        
    conn.execute("DELETE FROM user_config_presets WHERE id = ?", (preset_id,))
    config = get_rotation_config(user_id)
    if row["is_active"]:
        next_preset = conn.execute("SELECT id FROM user_config_presets WHERE user_id = ? ORDER BY created_at DESC LIMIT 1", (user_id,)).fetchone()
        if next_preset:
            conn.execute("UPDATE user_config_presets SET is_active = 1 WHERE id = ?", (next_preset["id"],))
    conn.commit()
    _delete_split_configs(preset_id, user_id)

    config = get_rotation_config(user_id)
    fallback_id = (get_active(user_id) or {}).get("id")
    for lane in ("llm", "embedding"):
        lane_config = config[lane]
        ids = [item for item in lane_config.get("preset_ids", []) if item != preset_id]
        active_id = lane_config.get("active_preset_id")
        if active_id == preset_id:
            active_id = fallback_id
        save_lane_rotation_config(user_id, lane, bool(lane_config.get("enabled")) and len(ids) >= 2, ids, active_id)

    _clear_settings_cache()
    return True


def _mirror_split_configs(preset_id: str, preset: dict[str, Any], user_id: str) -> None:
    conn = get_connection()
    existing_llm = conn.execute("SELECT llm_api_key FROM user_llm_configs WHERE id = ? AND user_id = ?", (f"llm-{preset_id}", user_id)).fetchone()
    existing_embedding = conn.execute("SELECT embedding_api_key FROM user_embedding_configs WHERE id = ? AND user_id = ?", (f"emb-{preset_id}", user_id)).fetchone()
    conn.execute(
        """
        INSERT INTO user_llm_configs (
            id, user_id, name, llm_provider, llm_model, llm_base_url, llm_api_key,
            llm_temperature, llm_max_retries, llm_max_tokens, llm_rate_limit_per_minute
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            llm_provider=excluded.llm_provider,
            llm_model=excluded.llm_model,
            llm_base_url=excluded.llm_base_url,
            llm_api_key=excluded.llm_api_key,
            llm_temperature=excluded.llm_temperature,
            llm_max_retries=excluded.llm_max_retries,
            llm_max_tokens=excluded.llm_max_tokens,
            llm_rate_limit_per_minute=excluded.llm_rate_limit_per_minute,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            f"llm-{preset_id}",
            user_id,
            preset.get("name", "Default"),
            preset.get("llm_provider", "openai"),
            preset.get("llm_model", "gpt-4o"),
            preset.get("llm_base_url"),
            preset.get("llm_api_key", existing_llm["llm_api_key"] if existing_llm else ""),
            float(preset.get("llm_temperature", 0)),
            int(preset.get("llm_max_retries", 2)),
            int(preset["llm_max_tokens"]) if preset.get("llm_max_tokens") is not None else None,
            int(preset.get("llm_rate_limit_per_minute", 0)),
        ),
    )
    conn.execute(
        """
        INSERT INTO user_embedding_configs (
            id, user_id, name, embedding_provider, embedding_model, embedding_base_url,
            embedding_api_key, embedding_rate_limit_per_minute, embedding_batch_size
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            embedding_provider=excluded.embedding_provider,
            embedding_model=excluded.embedding_model,
            embedding_base_url=excluded.embedding_base_url,
            embedding_api_key=excluded.embedding_api_key,
            embedding_rate_limit_per_minute=excluded.embedding_rate_limit_per_minute,
            embedding_batch_size=excluded.embedding_batch_size,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            f"emb-{preset_id}",
            user_id,
            preset.get("name", "Default"),
            preset.get("embedding_provider", "openai"),
            preset.get("embedding_model", "text-embedding-3-small"),
            preset.get("embedding_base_url"),
            preset.get("embedding_api_key", existing_embedding["embedding_api_key"] if existing_embedding else ""),
            int(preset.get("embedding_rate_limit_per_minute", 0)),
            int(preset.get("embedding_batch_size", 100)),
        ),
    )
    conn.commit()


def _delete_split_configs(preset_id: str, user_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM user_llm_configs WHERE id = ? AND user_id = ?", (f"llm-{preset_id}", user_id))
    conn.execute("DELETE FROM user_embedding_configs WHERE id = ? AND user_id = ?", (f"emb-{preset_id}", user_id))
    conn.commit()


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


def _owned_active_id(user_id: str, preset_id: str | None) -> str | None:
    if not preset_id:
        return None
    return preset_id if get_by_id(preset_id, user_id) else None


def _rotation_config_response(user_id: str, row: dict[str, Any], active_id: str | None) -> dict[str, Any]:
    legacy_ids = _json_list(row.get("preset_ids"))
    legacy_enabled = bool(row.get("enabled"))
    raw_llm_ids = _json_list(row.get("llm_preset_ids"))
    raw_embedding_ids = _json_list(row.get("embedding_preset_ids"))
    llm_ids = raw_llm_ids or (legacy_ids if legacy_enabled else [])
    embedding_ids = raw_embedding_ids or (legacy_ids if legacy_enabled else [])
    llm_enabled = bool(row.get("llm_enabled") or (legacy_enabled and not raw_llm_ids))
    embedding_enabled = bool(row.get("embedding_enabled") or (legacy_enabled and not raw_embedding_ids))
    llm_active = _owned_active_id(user_id, row.get("llm_active_preset_id")) or active_id
    embedding_active = _owned_active_id(user_id, row.get("embedding_active_preset_id")) or active_id
    return {
        "user_id": user_id,
        "enabled": 1 if llm_enabled and embedding_enabled and llm_ids == embedding_ids else 0,
        "preset_ids": llm_ids if llm_ids == embedding_ids else [],
        "llm": {
            "enabled": llm_enabled,
            "preset_ids": llm_ids,
            "active_preset_id": llm_active,
        },
        "embedding": {
            "enabled": embedding_enabled,
            "preset_ids": embedding_ids,
            "active_preset_id": embedding_active,
        },
    }


def _json_list(value: Any) -> list[str]:
    try:
        items = json.loads(value) if isinstance(value, str) else value
    except json.JSONDecodeError:
        items = []
    return [str(item) for item in items] if isinstance(items, list) else []


def _clear_settings_cache() -> None:
    from src.infra.settings import (
        get_user_embedding_setting_candidates,
        get_user_embedding_settings,
        get_user_llm_setting_candidates,
        get_user_llm_settings,
        get_user_setting_candidates,
        get_user_settings,
    )

    get_user_settings.cache_clear()
    get_user_setting_candidates.cache_clear()
    get_user_llm_settings.cache_clear()
    get_user_llm_setting_candidates.cache_clear()
    get_user_embedding_settings.cache_clear()
    get_user_embedding_setting_candidates.cache_clear()
