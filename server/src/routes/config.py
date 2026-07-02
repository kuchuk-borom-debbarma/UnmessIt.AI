import re
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field, field_validator

from src.infra.settings import Settings
from src.infra.settings import parse_retry_backoff_seconds
from src.infra.langchain_json import _get_chat_llm
from src.infra.chroma import _embedding_function_for_key
from src.routes.auth_utils import get_current_user_id
from src.repositories import config_presets

router = APIRouter(prefix="/configs", tags=["Config"])


class PresetCreate(BaseModel):
    name: str = "Default"
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_temperature: float = 0.0
    llm_max_retries: int = 2
    llm_max_tokens: int | None = None
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_base_url: str | None = None
    embedding_api_key: str | None = None
    llm_rate_limit_per_minute: int = 0
    embedding_rate_limit_per_minute: int = 0
    embedding_batch_size: int = 100
    chunk_size: int = 1000
    chunk_overlap: int = 200
    ingest_retry_backoff_seconds: str = "5,15,30,60,120"

    @field_validator("llm_provider", "embedding_provider")
    @classmethod
    def openai_only(cls, value: str) -> str:
        normalized = value.lower()
        if normalized != "openai":
            raise ValueError("Only OpenAI provider is supported")
        return normalized

    @field_validator("ingest_retry_backoff_seconds")
    @classmethod
    def valid_backoff(cls, value: str) -> str:
        return ",".join(str(item) for item in parse_retry_backoff_seconds(value))


class ProcessingSettingsPayload(BaseModel):
    embedding_batch_size: int = 100
    chunk_size: int = 1000
    chunk_overlap: int = 200
    ingest_retry_backoff_seconds: str = "5,15,30,60,120"

    @field_validator("ingest_retry_backoff_seconds")
    @classmethod
    def valid_backoff(cls, value: str) -> str:
        return ",".join(str(item) for item in parse_retry_backoff_seconds(value))


class RotationLanePayload(BaseModel):
    enabled: bool = False
    preset_ids: list[str] = Field(default_factory=list)
    active_preset_id: str | None = None


class RotationConfigPayload(BaseModel):
    enabled: bool | None = None
    preset_ids: list[str] | None = None
    llm: RotationLanePayload | None = None
    embedding: RotationLanePayload | None = None


class ConfigTestPayload(BaseModel):
    kind: Literal["llm", "embedding"]
    config: PresetCreate
    preset_id: str | None = None


class PresetResponse(BaseModel):
    id: str
    name: str
    is_active: int
    llm_provider: str
    llm_model: str
    llm_base_url: str | None
    llm_temperature: float
    llm_max_retries: int
    llm_max_tokens: int | None = None
    embedding_provider: str
    embedding_model: str
    embedding_base_url: str | None
    llm_rate_limit_per_minute: int
    embedding_rate_limit_per_minute: int
    embedding_batch_size: int
    chunk_size: int
    chunk_overlap: int
    ingest_retry_backoff_seconds: str


@router.get("/presets")
def list_presets(user_id: str = Depends(get_current_user_id)) -> list[dict[str, Any]]:
    """List all presets for the current user."""
    presets = config_presets.list_for_user(user_id)
    rotation = config_presets.get_rotation_config(user_id)
    # Filter out API keys for list view security
    for preset in presets:
        preset.pop("llm_api_key", None)
        preset.pop("embedding_api_key", None)
        preset["llm_is_active"] = 1 if not rotation["llm"].get("enabled") and preset["id"] == rotation["llm"].get("active_preset_id") else 0
        preset["embedding_is_active"] = 1 if not rotation["embedding"].get("enabled") and preset["id"] == rotation["embedding"].get("active_preset_id") else 0
    return presets


@router.get("/processing")
def get_processing_config(user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    """Get stable processing settings."""
    settings = config_presets.get_processing(user_id)
    return _processing_response(settings)


@router.put("/processing")
def update_processing_config(payload: ProcessingSettingsPayload, user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    """Save stable processing settings."""
    config_presets.save_processing(payload.model_dump(), user_id)
    return _processing_response(config_presets.get_processing(user_id))


@router.get("/rotation")
def get_rotation_config(user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    """Get ordered per-job/request rotation config."""
    return _rotation_response(user_id)


@router.put("/rotation")
def update_rotation_config(payload: RotationConfigPayload, user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    """Save ordered per-job/request rotation config."""
    try:
        if payload.llm or payload.embedding:
            current = config_presets.get_rotation_config(user_id)
            llm = payload.llm or RotationLanePayload(**current["llm"])
            embedding = payload.embedding or RotationLanePayload(**current["embedding"])
            config_presets.save_split_rotation_config(
                user_id,
                llm_enabled=llm.enabled,
                llm_preset_ids=llm.preset_ids,
                embedding_enabled=embedding.enabled,
                embedding_preset_ids=embedding.preset_ids,
                llm_active_preset_id=llm.active_preset_id,
                embedding_active_preset_id=embedding.active_preset_id,
            )
        else:
            config_presets.save_rotation_config(user_id, bool(payload.enabled), payload.preset_ids or [])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _rotation_response(user_id)


@router.post("/test")
def test_config(payload: ConfigTestPayload, user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    """Test one unsaved LLM or embedding config against the upstream API."""
    config = payload.config.model_dump()
    if payload.preset_id:
        existing = config_presets.get_by_id(payload.preset_id, user_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preset not found")
        if not config.get("llm_api_key"):
            config["llm_api_key"] = existing.get("llm_api_key", "")
        if not config.get("embedding_api_key"):
            config["embedding_api_key"] = existing.get("embedding_api_key", "")

    settings = Settings(config)
    try:
        if payload.kind == "llm":
            _get_chat_llm(settings.llm_cache_key()).invoke([HumanMessage(content='Reply with "ok".')])
        else:
            _embedding_function_for_key(settings.embedding_cache_key())(["UnmessIt API test"])
    except Exception as exc:
        upstream_status = _upstream_status(exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "kind": "api",
                "message": _friendly_provider_error(payload.kind, upstream_status),
                "upstream_status": upstream_status,
                "error": _safe_error(exc),
            },
        ) from exc
    return {
        "status": "ok",
        "status_code": 200,
        "kind": payload.kind,
        "message": f"{payload.kind.upper()} API test returned 200.",
    }


@router.post("/presets")
def create_preset(payload: PresetCreate, user_id: str = Depends(get_current_user_id)) -> dict[str, str]:
    """Create a new preset."""
    preset_dict = payload.model_dump(exclude_unset=True)
    preset_id = config_presets.save(preset_dict, user_id)
    return {"id": preset_id}


@router.put("/presets/{preset_id}")
def update_preset(preset_id: str, payload: PresetCreate, user_id: str = Depends(get_current_user_id)) -> dict[str, str]:
    """Update an existing preset."""
    existing = config_presets.get_by_id(preset_id, user_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preset not found")
    
    preset_dict = payload.model_dump(exclude_unset=True)
    preset_dict["id"] = preset_id
    preset_dict["is_active"] = existing.get("is_active", 0)
    
    if not preset_dict.get("llm_api_key"):
        preset_dict["llm_api_key"] = existing.get("llm_api_key", "")
    if not preset_dict.get("embedding_api_key"):
        preset_dict["embedding_api_key"] = existing.get("embedding_api_key", "")
        
    config_presets.save(preset_dict, user_id)
    return {"id": preset_id}


@router.put("/presets/{preset_id}/activate")
def activate_preset(preset_id: str, lane: Literal["both", "llm", "embedding"] = Query("both"), user_id: str = Depends(get_current_user_id)) -> dict[str, str]:
    """Activate a specific preset."""
    if lane == "both" and config_presets.set_active(preset_id, user_id):
        return {"status": "ok"}
    if lane != "both" and config_presets.set_active_lane(preset_id, user_id, lane):
        return {"status": "ok"}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preset not found")


@router.delete("/presets/{preset_id}")
def delete_preset(preset_id: str, user_id: str = Depends(get_current_user_id)) -> dict[str, str]:
    """Delete a preset."""
    if config_presets.delete(preset_id, user_id):
        return {"status": "ok"}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preset not found")


@router.get("/active")
def get_active_config(user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    """Get the currently effective active configuration."""
    from src.infra.settings import get_user_embedding_settings, get_user_llm_settings
    llm_settings = get_user_llm_settings(user_id)
    embedding_settings = get_user_embedding_settings(user_id)
    return {
        "llm_provider": llm_settings.llm_provider,
        "llm_model": llm_settings.llm_model,
        "llm_base_url": llm_settings.llm_base_url,
        "llm_temperature": llm_settings.llm_temperature,
        "llm_max_retries": llm_settings.llm_max_retries,
        "llm_max_tokens": llm_settings.llm_max_tokens,
        "embedding_provider": embedding_settings.embedding_provider,
        "embedding_model": embedding_settings.embedding_model,
        "embedding_base_url": embedding_settings.embedding_base_url,
        "llm_rate_limit_per_minute": llm_settings.llm_rate_limit_per_minute,
        "embedding_rate_limit_per_minute": embedding_settings.embedding_rate_limit_per_minute,
        "embedding_batch_size": embedding_settings.embedding_batch_size,
        "chunk_size": embedding_settings.chunk_size,
        "chunk_overlap": embedding_settings.chunk_overlap,
        "ingest_retry_backoff_seconds": ",".join(str(item) for item in embedding_settings.ingest_retry_backoff_seconds),
    }


def _processing_response(settings: dict[str, Any]) -> dict[str, Any]:
    return {
        "embedding_batch_size": int(settings.get("embedding_batch_size", 100)),
        "chunk_size": int(settings.get("chunk_size", 1000)),
        "chunk_overlap": int(settings.get("chunk_overlap", 200)),
        "ingest_retry_backoff_seconds": settings.get("ingest_retry_backoff_seconds", "5,15,30,60,120"),
    }


def _rotation_response(user_id: str) -> dict[str, Any]:
    config = config_presets.get_rotation_config(user_id)
    llm_presets = [_public_preset(preset) for preset in config_presets.llm_rotation_candidates(user_id)]
    embedding_presets = [_public_preset(preset) for preset in config_presets.embedding_rotation_candidates(user_id)]
    return {
        "enabled": bool(config.get("enabled")),
        "preset_ids": config.get("preset_ids", []),
        "presets": llm_presets,
        "llm": {**config["llm"], "presets": llm_presets},
        "embedding": {**config["embedding"], "presets": embedding_presets},
    }


def _public_preset(preset: dict[str, Any]) -> dict[str, Any]:
    clean = dict(preset)
    clean.pop("llm_api_key", None)
    clean.pop("embedding_api_key", None)
    return clean


def _upstream_status(exc: Exception) -> int | None:
    for value in (getattr(exc, "status_code", None), getattr(getattr(exc, "response", None), "status_code", None)):
        if isinstance(value, int):
            return value
    match = re.search(r"(?:status|code)\D+([45]\d\d)", str(exc), re.IGNORECASE)
    return int(match.group(1)) if match else None


def _safe_error(exc: Exception) -> str:
    text = str(exc) or exc.__class__.__name__
    return text[:800]


def _friendly_provider_error(kind: str, upstream_status: int | None) -> str:
    label = "LLM" if kind == "llm" else "Embedding"
    if upstream_status == 401:
        return f"{label} provider rejected the credentials (401). Update the API key, base URL, or provider account access."
    if upstream_status == 404:
        return f"{label} provider returned 404. Check the model name and base URL."
    if upstream_status == 429:
        return f"{label} provider rate-limited the request (429). Lower the rate limit or wait before retrying."
    if upstream_status and upstream_status >= 500:
        return f"{label} provider returned {upstream_status}. The provider service may be down or overloaded."
    return f"{label} API test failed. Check the key, model, base URL, and provider account access."
