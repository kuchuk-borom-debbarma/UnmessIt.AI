from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from src.infra.settings import parse_retry_backoff_seconds
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


class RotationConfigPayload(BaseModel):
    enabled: bool = False
    preset_ids: list[str] = []


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
    # Filter out API keys for list view security
    for preset in presets:
        preset.pop("llm_api_key", None)
        preset.pop("embedding_api_key", None)
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
        config_presets.save_rotation_config(user_id, payload.enabled, payload.preset_ids)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _rotation_response(user_id)


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
def activate_preset(preset_id: str, user_id: str = Depends(get_current_user_id)) -> dict[str, str]:
    """Activate a specific preset."""
    if config_presets.set_active(preset_id, user_id):
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
    from src.infra.settings import get_user_settings
    settings = get_user_settings(user_id)
    return {
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "llm_base_url": settings.llm_base_url,
        "llm_temperature": settings.llm_temperature,
        "llm_max_retries": settings.llm_max_retries,
        "llm_max_tokens": settings.llm_max_tokens,
        "embedding_provider": settings.embedding_provider,
        "embedding_model": settings.embedding_model,
        "embedding_base_url": settings.embedding_base_url,
        "llm_rate_limit_per_minute": settings.llm_rate_limit_per_minute,
        "embedding_rate_limit_per_minute": settings.embedding_rate_limit_per_minute,
        "embedding_batch_size": settings.embedding_batch_size,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "ingest_retry_backoff_seconds": ",".join(str(item) for item in settings.ingest_retry_backoff_seconds),
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
    presets = [_public_preset(preset) for preset in config_presets.rotation_candidates(user_id)] if config.get("enabled") else []
    return {
        "enabled": bool(config.get("enabled")),
        "preset_ids": config.get("preset_ids", []),
        "presets": presets,
    }


def _public_preset(preset: dict[str, Any]) -> dict[str, Any]:
    clean = dict(preset)
    clean.pop("llm_api_key", None)
    clean.pop("embedding_api_key", None)
    return clean
