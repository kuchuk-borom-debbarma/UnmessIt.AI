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
from src.repositories import config_presets, config_profiles

router = APIRouter(prefix="/configs", tags=["Config"])


class ProcessingSettingsPayload(BaseModel):
    embedding_batch_size: int = 100
    chunk_size: int = 1000
    chunk_overlap: int = 200
    ingest_retry_backoff_seconds: str = "5,15,30,60,120"

    @field_validator("ingest_retry_backoff_seconds")
    @classmethod
    def valid_backoff(cls, value: str) -> str:
        return ",".join(str(item) for item in parse_retry_backoff_seconds(value))


class LLMConfigPayload(BaseModel):
    name: str = "LLM"
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_temperature: float = 0.0
    llm_max_retries: int = 2
    llm_max_tokens: int | None = None
    llm_rate_limit_per_minute: int = 0

    @field_validator("llm_provider")
    @classmethod
    def openai_only(cls, value: str) -> str:
        normalized = value.lower()
        if normalized != "openai":
            raise ValueError("Only OpenAI provider is supported")
        return normalized


class EmbeddingConfigPayload(BaseModel):
    name: str = "Embedding"
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_base_url: str | None = None
    embedding_api_key: str | None = None
    embedding_rate_limit_per_minute: int = 0
    embedding_batch_size: int = 100

    @field_validator("embedding_provider")
    @classmethod
    def openai_only(cls, value: str) -> str:
        normalized = value.lower()
        if normalized != "openai":
            raise ValueError("Only OpenAI provider is supported")
        return normalized


class StageConfigPayload(BaseModel):
    kind: Literal["llm", "embedding"]
    enabled: bool = False
    config_ids: list[str] = Field(default_factory=list)
    active_config_id: str | None = None


class ConfigTestPayload(BaseModel):
    kind: Literal["llm", "embedding"]
    config: dict[str, Any]
    config_id: str | None = None


@router.get("/llm")
def list_llm_configs(user_id: str = Depends(get_current_user_id)) -> list[dict[str, Any]]:
    return [_public_llm_config(item) for item in config_profiles.list_llm(user_id)]


@router.post("/llm")
def create_llm_config(payload: LLMConfigPayload, user_id: str = Depends(get_current_user_id)) -> dict[str, str]:
    return {"id": config_profiles.save_llm(payload.model_dump(exclude_unset=True), user_id)}


@router.put("/llm/{config_id}")
def update_llm_config(config_id: str, payload: LLMConfigPayload, user_id: str = Depends(get_current_user_id)) -> dict[str, str]:
    existing = config_profiles.get_llm(config_id, user_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LLM config not found")
    data = payload.model_dump(exclude_unset=True)
    data["id"] = config_id
    if not data.get("llm_api_key"):
        data["llm_api_key"] = existing.get("llm_api_key", "")
    return {"id": config_profiles.save_llm(data, user_id)}


@router.delete("/llm/{config_id}")
def delete_llm_config(config_id: str, user_id: str = Depends(get_current_user_id)) -> dict[str, str]:
    if config_profiles.delete_llm(config_id, user_id):
        return {"status": "ok"}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LLM config not found")


@router.get("/embedding")
def list_embedding_configs(user_id: str = Depends(get_current_user_id)) -> list[dict[str, Any]]:
    return [_public_embedding_config(item) for item in config_profiles.list_embedding(user_id)]


@router.post("/embedding")
def create_embedding_config(payload: EmbeddingConfigPayload, user_id: str = Depends(get_current_user_id)) -> dict[str, str]:
    return {"id": config_profiles.save_embedding(payload.model_dump(exclude_unset=True), user_id)}


@router.put("/embedding/{config_id}")
def update_embedding_config(config_id: str, payload: EmbeddingConfigPayload, user_id: str = Depends(get_current_user_id)) -> dict[str, str]:
    existing = config_profiles.get_embedding(config_id, user_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Embedding config not found")
    data = payload.model_dump(exclude_unset=True)
    data["id"] = config_id
    if not data.get("embedding_api_key"):
        data["embedding_api_key"] = existing.get("embedding_api_key", "")
    return {"id": config_profiles.save_embedding(data, user_id)}


@router.delete("/embedding/{config_id}")
def delete_embedding_config(config_id: str, user_id: str = Depends(get_current_user_id)) -> dict[str, str]:
    if config_profiles.delete_embedding(config_id, user_id):
        return {"status": "ok"}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Embedding config not found")


@router.get("/stages")
def get_stage_configs(user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    return _stage_response(user_id)


@router.put("/stages/{stage}")
def update_stage_config(stage: str, payload: StageConfigPayload, user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    try:
        config_profiles.save_stage(user_id, stage, payload.kind, payload.enabled, payload.config_ids, payload.active_config_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _stage_response(user_id)


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


@router.post("/test")
def test_config(payload: ConfigTestPayload, user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    """Test one unsaved LLM or embedding config against the upstream API."""
    config = payload.config
    if payload.config_id:
        if payload.kind == "llm":
            existing = config_profiles.get_llm(payload.config_id, user_id)
            if not existing:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LLM config not found")
            if not config.get("llm_api_key"):
                config["llm_api_key"] = existing.get("llm_api_key", "")
        else:
            existing = config_profiles.get_embedding(payload.config_id, user_id)
            if not existing:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Embedding config not found")
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


def _processing_response(settings: dict[str, Any]) -> dict[str, Any]:
    return {
        "embedding_batch_size": int(settings.get("embedding_batch_size", 100)),
        "chunk_size": int(settings.get("chunk_size", 1000)),
        "chunk_overlap": int(settings.get("chunk_overlap", 200)),
        "ingest_retry_backoff_seconds": settings.get("ingest_retry_backoff_seconds", "5,15,30,60,120"),
    }


def _stage_response(user_id: str) -> dict[str, Any]:
    return {
        **config_profiles.get_stages(user_id),
        "llm_configs": [_public_llm_config(item) for item in config_profiles.list_llm(user_id)],
        "embedding_configs": [_public_embedding_config(item) for item in config_profiles.list_embedding(user_id)],
    }


def _public_llm_config(config: dict[str, Any]) -> dict[str, Any]:
    clean = dict(config)
    clean.pop("llm_api_key", None)
    return clean


def _public_embedding_config(config: dict[str, Any]) -> dict[str, Any]:
    clean = dict(config)
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
