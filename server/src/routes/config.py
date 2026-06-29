from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.routes.auth_utils import get_current_user_id
from src.repositories import config_presets

router = APIRouter(prefix="/configs", tags=["Config"])


class PresetCreate(BaseModel):
    name: str = "Default"
    llm_provider: str = "ollama"
    llm_model: str = "llama3.2:latest"
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_temperature: float = 0.0
    llm_max_retries: int = 2
    llm_max_tokens: int = 2048
    embedding_provider: str = "ollama"
    embedding_model: str = "nomic-embed-text"
    embedding_base_url: str | None = None
    embedding_api_key: str | None = None
    chunk_size: int = 1000
    chunk_overlap: int = 200


class PresetResponse(BaseModel):
    id: str
    name: str
    is_active: int
    llm_provider: str
    llm_model: str
    llm_base_url: str | None
    llm_temperature: float
    llm_max_retries: int
    llm_max_tokens: int
    embedding_provider: str
    embedding_model: str
    embedding_base_url: str | None
    chunk_size: int
    chunk_overlap: int


@router.get("/presets")
def list_presets(user_id: str = Depends(get_current_user_id)) -> list[dict[str, Any]]:
    """List all presets for the current user."""
    presets = config_presets.list_for_user(user_id)
    # Filter out API keys for list view security
    for preset in presets:
        preset.pop("llm_api_key", None)
        preset.pop("embedding_api_key", None)
    return presets


@router.post("/presets")
def create_preset(payload: PresetCreate, user_id: str = Depends(get_current_user_id)) -> dict[str, str]:
    """Create a new preset."""
    preset_dict = payload.model_dump(exclude_unset=True)
    preset_id = config_presets.save(preset_dict, user_id)
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
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
    }
