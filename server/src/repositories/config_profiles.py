from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from src.infra.sqlite import get_connection

LLM_STAGES = (
    "ingest.source_chunk_draft",
    "ingest.recall_draft",
    "retrieval.query_breakdown",
    "retrieval.subject_extraction",
    "retrieval.verifier",
    "retrieval.answer",
)

EMBEDDING_STAGES = (
    "ingest.source_chunk_vectors",
    "ingest.recall_key_vectors",
    "retrieval.vector_search",
    "retrieval.semantic_cache",
)


def list_llm(user_id: str) -> list[dict[str, Any]]:
    rows = get_connection().execute(
        "SELECT * FROM user_llm_configs WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def list_embedding(user_id: str) -> list[dict[str, Any]]:
    rows = get_connection().execute(
        "SELECT * FROM user_embedding_configs WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_llm(config_id: str, user_id: str) -> dict[str, Any] | None:
    row = get_connection().execute(
        "SELECT * FROM user_llm_configs WHERE id = ? AND user_id = ?",
        (config_id, user_id),
    ).fetchone()
    return dict(row) if row else None


def get_embedding(config_id: str, user_id: str) -> dict[str, Any] | None:
    row = get_connection().execute(
        "SELECT * FROM user_embedding_configs WHERE id = ? AND user_id = ?",
        (config_id, user_id),
    ).fetchone()
    return dict(row) if row else None


def save_llm(config: dict[str, Any], user_id: str) -> str:
    config_id = config.get("id") or str(uuid4())
    get_connection().execute(
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
            config_id,
            user_id,
            config.get("name", "LLM"),
            config.get("llm_provider", "openai").lower(),
            config.get("llm_model", "gpt-4o"),
            config.get("llm_base_url"),
            config.get("llm_api_key", ""),
            float(config.get("llm_temperature", 0)),
            int(config.get("llm_max_retries", 2)),
            int(config["llm_max_tokens"]) if config.get("llm_max_tokens") is not None else None,
            int(config.get("llm_rate_limit_per_minute", 0)),
        ),
    )
    get_connection().commit()
    _clear_settings_cache()
    return config_id


def save_embedding(config: dict[str, Any], user_id: str) -> str:
    config_id = config.get("id") or str(uuid4())
    get_connection().execute(
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
            config_id,
            user_id,
            config.get("name", "Embedding"),
            config.get("embedding_provider", "openai").lower(),
            config.get("embedding_model", "text-embedding-3-small"),
            config.get("embedding_base_url"),
            config.get("embedding_api_key", ""),
            int(config.get("embedding_rate_limit_per_minute", 0)),
            int(config.get("embedding_batch_size", 100)),
        ),
    )
    get_connection().commit()
    _clear_settings_cache()
    return config_id


def delete_llm(config_id: str, user_id: str) -> bool:
    deleted = get_connection().execute(
        "DELETE FROM user_llm_configs WHERE id = ? AND user_id = ?",
        (config_id, user_id),
    ).rowcount
    get_connection().commit()
    _clear_settings_cache()
    return bool(deleted)


def delete_embedding(config_id: str, user_id: str) -> bool:
    deleted = get_connection().execute(
        "DELETE FROM user_embedding_configs WHERE id = ? AND user_id = ?",
        (config_id, user_id),
    ).rowcount
    get_connection().commit()
    _clear_settings_cache()
    return bool(deleted)


def get_stages(user_id: str) -> dict[str, Any]:
    return {
        "llm": {stage: _stage_response(user_id, stage, "llm") for stage in LLM_STAGES},
        "embedding": {stage: _stage_response(user_id, stage, "embedding") for stage in EMBEDDING_STAGES},
    }


def save_stage(user_id: str, stage: str, kind: str, enabled: bool, config_ids: list[str], active_config_id: str | None) -> dict[str, Any]:
    if kind == "llm" and stage not in LLM_STAGES:
        raise ValueError("Unknown LLM stage.")
    if kind == "embedding" and stage not in EMBEDDING_STAGES:
        raise ValueError("Unknown embedding stage.")
    ids = _owned_ids(user_id, kind, config_ids)
    active = _owned_active_id(user_id, kind, active_config_id) or _default_active_id(user_id, kind)
    get_connection().execute(
        """
        INSERT INTO user_stage_config (user_id, stage, kind, enabled, config_ids, active_config_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, stage) DO UPDATE SET
            kind=excluded.kind,
            enabled=excluded.enabled,
            config_ids=excluded.config_ids,
            active_config_id=excluded.active_config_id,
            updated_at=CURRENT_TIMESTAMP
        """,
        (user_id, stage, kind, 1 if enabled else 0, json.dumps(ids, ensure_ascii=False), active),
    )
    get_connection().commit()
    _clear_settings_cache()
    return _stage_response(user_id, stage, kind)


def llm_candidates(user_id: str, stage: str | None = None) -> list[dict[str, Any]]:
    if stage is None:
        from src.repositories import config_presets

        legacy = config_presets.llm_rotation_candidates(user_id)
        if legacy:
            return legacy
    candidates = _candidates(user_id, stage or "retrieval.answer", "llm")
    if candidates:
        return candidates
    from src.repositories import config_presets

    return config_presets.llm_rotation_candidates(user_id)


def embedding_candidates(user_id: str, stage: str | None = None) -> list[dict[str, Any]]:
    if stage is None:
        from src.repositories import config_presets

        legacy = config_presets.embedding_rotation_candidates(user_id)
        if legacy:
            return legacy
    candidates = _candidates(user_id, stage or "retrieval.vector_search", "embedding")
    if candidates:
        return candidates
    from src.repositories import config_presets

    return config_presets.embedding_rotation_candidates(user_id)


def _candidates(user_id: str, stage: str, kind: str) -> list[dict[str, Any]]:
    stage_config = _stage_response(user_id, stage, kind)
    if stage_config["enabled"]:
        return [config for config in _by_order(user_id, kind, stage_config["config_ids"]) if config]
    config = _get(kind, str(stage_config.get("active_config_id") or ""), user_id)
    return [config] if config else []


def _stage_response(user_id: str, stage: str, kind: str) -> dict[str, Any]:
    row = get_connection().execute(
        "SELECT * FROM user_stage_config WHERE user_id = ? AND stage = ?",
        (user_id, stage),
    ).fetchone()
    if row:
        data = dict(row)
        ids = _owned_ids(user_id, kind, _json_list(data.get("config_ids")))
        return {
            "stage": stage,
            "kind": kind,
            "enabled": bool(data.get("enabled")),
            "config_ids": ids,
            "active_config_id": _owned_active_id(user_id, kind, data.get("active_config_id")) or _default_active_id(user_id, kind),
        }
    return {
        "stage": stage,
        "kind": kind,
        "enabled": False,
        "config_ids": [],
        "active_config_id": _default_active_id(user_id, kind),
    }


def _default_active_id(user_id: str, kind: str) -> str | None:
    from src.repositories import config_presets

    legacy = config_presets.get_rotation_config(user_id)
    legacy_id = legacy.get(kind, {}).get("active_preset_id")
    if legacy_id:
        split_id = ("llm-" if kind == "llm" else "emb-") + str(legacy_id)
        if _get(kind, split_id, user_id):
            return split_id
    configs = list_llm(user_id) if kind == "llm" else list_embedding(user_id)
    if not configs:
        return None
    return configs[0]["id"]


def _owned_ids(user_id: str, kind: str, ids: list[str]) -> list[str]:
    owned = {config["id"] for config in (list_llm(user_id) if kind == "llm" else list_embedding(user_id))}
    clean: list[str] = []
    for config_id in ids:
        if config_id in owned and config_id not in clean:
            clean.append(config_id)
    return clean


def _owned_active_id(user_id: str, kind: str, config_id: str | None) -> str | None:
    if not config_id:
        return None
    return config_id if _get(kind, config_id, user_id) else None


def _get(kind: str, config_id: str, user_id: str) -> dict[str, Any] | None:
    return get_llm(config_id, user_id) if kind == "llm" else get_embedding(config_id, user_id)


def _by_order(user_id: str, kind: str, ids: list[str]) -> list[dict[str, Any]]:
    configs = list_llm(user_id) if kind == "llm" else list_embedding(user_id)
    by_id = {config["id"]: config for config in configs}
    return [by_id[config_id] for config_id in ids if config_id in by_id]


def _json_list(value: Any) -> list[str]:
    try:
        items = json.loads(value) if isinstance(value, str) else value
    except json.JSONDecodeError:
        items = []
    return [str(item) for item in items] if isinstance(items, list) else []


def _clear_settings_cache() -> None:
    from src.repositories import config_presets

    config_presets._clear_settings_cache()
