from __future__ import annotations

import os
from functools import lru_cache
from urllib.parse import urlsplit, urlunsplit

try:
    from dotenv import find_dotenv, load_dotenv
except ModuleNotFoundError:
    find_dotenv = lambda: ""
    load_dotenv = lambda _path="": False

load_dotenv(find_dotenv())

class NoActivePresetError(Exception):
    """Raised when an operation requires an AI preset but the user has none active."""
    pass

class Settings:
    def __init__(self, preset: dict | None = None, processing: dict | None = None) -> None:
        preset = preset or {}
        processing = processing or preset or {}
        
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.enable_dev_routes = os.getenv("ENABLE_DEV_ROUTES", "1").lower() not in {"0", "false", "no"}
        self.cors_origins = [item.strip() for item in os.getenv("CORS_ORIGINS", "*").split(",") if item.strip()]

        self.llm_provider = (preset.get("llm_provider") or "openai").lower()
        self.llm_model = preset.get("llm_model") or "gpt-4o"
        self.llm_base_url = _docker_reachable_url(preset.get("llm_base_url"))
        self.llm_api_key = preset.get("llm_api_key") or ""
        self.llm_temperature = float(preset.get("llm_temperature", 0.0))
        self.llm_max_retries = int(preset.get("llm_max_retries", 2))
        self.llm_max_tokens = int(preset["llm_max_tokens"]) if preset.get("llm_max_tokens") is not None else None
        self.llm_rate_limit_per_minute = int(preset.get("llm_rate_limit_per_minute", 0))

        self.preset_id = str(preset.get("id") or "")
        self.preset_name = str(preset.get("name") or "Default")

        self.embedding_provider = (preset.get("embedding_provider") or "openai").lower()
        self.embedding_model = preset.get("embedding_model") or "text-embedding-3-small"
        self.embedding_base_url = _docker_reachable_url(preset.get("embedding_base_url"))
        self.embedding_api_key = preset.get("embedding_api_key") or ""
        self.embedding_rate_limit_per_minute = int(preset.get("embedding_rate_limit_per_minute", 0))
        self.embedding_batch_size = int(processing.get("embedding_batch_size", 100))
        
        self.chunk_size = int(processing.get("chunk_size", 1000))
        self.chunk_overlap = int(processing.get("chunk_overlap", 200))
        self.ingest_retry_backoff_seconds = parse_retry_backoff_seconds(
            processing.get("ingest_retry_backoff_seconds")
        )

    def llm_cache_key(self) -> tuple:
        return (
            self.preset_id,
            self.llm_provider,
            self.llm_model,
            self.llm_base_url,
            self.llm_api_key,
            self.llm_temperature,
            self.llm_max_retries,
            self.llm_max_tokens,
            self.llm_rate_limit_per_minute,
        )

    def embedding_cache_key(self) -> tuple:
        return (
            self.preset_id,
            self.embedding_provider,
            self.embedding_model,
            self.embedding_base_url,
            self.embedding_api_key,
            self.embedding_rate_limit_per_minute,
        )

    def processing_signature(self) -> str:
        return "|".join([
            self.embedding_provider,
            self.embedding_model,
            str(self.chunk_size),
            str(self.chunk_overlap),
            str(self.embedding_batch_size),
        ])

    def processing_snapshot(self) -> dict:
        return {
            "embedding_batch_size": self.embedding_batch_size,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "ingest_retry_backoff_seconds": ",".join(str(item) for item in self.ingest_retry_backoff_seconds),
        }

    def rotation_snapshot(self) -> dict:
        return {
            "preset_id": self.preset_id,
            "preset_name": self.preset_name,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "llm_base_url": self.llm_base_url,
            "embedding_provider": self.embedding_provider,
            "embedding_model": self.embedding_model,
            "embedding_base_url": self.embedding_base_url,
            "llm_rate_limit_per_minute": self.llm_rate_limit_per_minute,
            "embedding_rate_limit_per_minute": self.embedding_rate_limit_per_minute,
        }


def parse_retry_backoff_seconds(value: object) -> list[int]:
    """Parse preset CSV retry delays, bounded enough to avoid typo foot-guns."""
    text = str(value or "5,15,30,60,120")
    seconds = []
    for part in text.split(","):
        try:
            item = int(part.strip())
        except ValueError:
            continue
        if 0 <= item <= 3600:
            seconds.append(item)
    return seconds[:10] or [5, 15, 30, 60, 120]


def _docker_reachable_url(url: str | None) -> str | None:
    if not url or os.getenv("UNMESSIT_DOCKER", "").lower() not in {"1", "true", "yes"}:
        return url
    parsed = urlsplit(url)
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        return url
    host = "host.docker.internal"
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return server runtime defaults."""
    return Settings()


@lru_cache(maxsize=128)
def get_user_settings(user_id: str) -> Settings:
    """Return the first effective legacy combined settings candidate."""
    candidates = get_user_setting_candidates(user_id)
    if not candidates:
        raise NoActivePresetError("No config configured. Please add one in Settings.")
    return candidates[0]


@lru_cache(maxsize=256)
def get_user_llm_settings(user_id: str, stage: str | None = None) -> Settings:
    """Return the first effective LLM settings candidate."""
    candidates = get_user_llm_setting_candidates(user_id, stage)
    if not candidates:
        raise NoActivePresetError("No LLM config configured. Please add one in Settings.")
    return candidates[0]


@lru_cache(maxsize=256)
def get_user_embedding_settings(user_id: str, stage: str | None = None) -> Settings:
    """Return the first effective embedding settings candidate."""
    candidates = get_user_embedding_setting_candidates(user_id, stage)
    if not candidates:
        raise NoActivePresetError("No embedding config configured. Please add one in Settings.")
    return candidates[0]


@lru_cache(maxsize=128)
def get_user_setting_candidates(user_id: str) -> tuple[Settings, ...]:
    """Return ordered legacy combined candidates for compatibility callers."""
    from src.repositories.config_presets import rotation_candidates

    return _setting_candidates(user_id, rotation_candidates, "config")


@lru_cache(maxsize=256)
def get_user_llm_setting_candidates(user_id: str, stage: str | None = None) -> tuple[Settings, ...]:
    """Return ordered per-job/request LLM candidates."""
    from src.repositories.config_profiles import llm_candidates

    return _setting_candidates(user_id, lambda uid: llm_candidates(uid, stage), "LLM")


@lru_cache(maxsize=256)
def get_user_embedding_setting_candidates(user_id: str, stage: str | None = None) -> tuple[Settings, ...]:
    """Return ordered per-job/request embedding candidates."""
    from src.repositories.config_profiles import embedding_candidates

    return _setting_candidates(user_id, lambda uid: embedding_candidates(uid, stage), "embedding")


def _setting_candidates(user_id: str, loader, label: str) -> tuple[Settings, ...]:
    from src.repositories.config_presets import get_processing

    # Non-user runtime paths get server defaults, never provider secrets.
    if not user_id:
        return (get_settings(),)

    processing = get_processing(user_id)
    presets = loader(user_id)
    if not presets:
        raise NoActivePresetError(f"No {label} config configured. Please add one in Settings.")
    return tuple(Settings(preset, processing) for preset in presets)
