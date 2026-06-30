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
    def __init__(self, preset: dict | None = None) -> None:
        preset = preset or {}
        
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.enable_dev_routes = os.getenv("ENABLE_DEV_ROUTES", "1").lower() not in {"0", "false", "no"}
        self.cors_origins = [item.strip() for item in os.getenv("CORS_ORIGINS", "*").split(",") if item.strip()]

        self.llm_provider = (preset.get("llm_provider") or "openai").lower()
        self.llm_model = preset.get("llm_model") or "gpt-4o"
        self.llm_base_url = _docker_reachable_url(preset.get("llm_base_url"))
        self.llm_api_key = preset.get("llm_api_key") or ""
        self.llm_temperature = float(preset.get("llm_temperature", 0.0))
        self.llm_max_retries = int(preset.get("llm_max_retries", 2))
        self.llm_max_tokens = int(preset.get("llm_max_tokens", 2048))
        self.llm_rate_limit_per_minute = int(preset.get("llm_rate_limit_per_minute", 0))

        self.embedding_provider = (preset.get("embedding_provider") or "openai").lower()
        self.embedding_model = preset.get("embedding_model") or "text-embedding-3-small"
        self.embedding_base_url = _docker_reachable_url(preset.get("embedding_base_url"))
        self.embedding_api_key = preset.get("embedding_api_key") or ""
        self.embedding_rate_limit_per_minute = int(preset.get("embedding_rate_limit_per_minute", 0))
        self.embedding_batch_size = int(preset.get("embedding_batch_size", 100))
        
        self.chunk_size = int(preset.get("chunk_size", 1000))
        self.chunk_overlap = int(preset.get("chunk_overlap", 200))
        self.ingest_retry_backoff_seconds = parse_retry_backoff_seconds(
            preset.get("ingest_retry_backoff_seconds")
        )


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
    """Return the active AI settings for a specific user."""
    from src.repositories.config_presets import get_active
    
    # Non-user runtime paths get server defaults, never provider secrets.
    if not user_id:
        return get_settings()
        
    preset = get_active(user_id)
    if not preset:
        raise NoActivePresetError("No active AI preset configured. Please configure an AI preset in Settings.")
    return Settings(preset)
