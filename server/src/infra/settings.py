from __future__ import annotations

import os
from functools import lru_cache

try:
    from dotenv import find_dotenv, load_dotenv
except ModuleNotFoundError:
    find_dotenv = lambda: ""
    load_dotenv = lambda _path="": False

load_dotenv(find_dotenv())


class Settings:
    def __init__(self, preset: dict | None = None) -> None:
        preset = preset or {}
        
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        self.llm_provider = preset.get("llm_provider") or os.getenv("INGEST_MODEL_PROVIDER", "ollama").lower()
        self.llm_model = preset.get("llm_model") or os.getenv("INGEST_MODEL_NAME", "llama3.2:latest")
        self.llm_base_url = preset.get("llm_base_url") or os.getenv("INGEST_MODEL_BASE_URL")
        self.llm_api_key = preset.get("llm_api_key") or os.getenv("INGEST_MODEL_API_KEY", "")
        self.llm_temperature = float(preset.get("llm_temperature", os.getenv("INGEST_MODEL_TEMPERATURE", "0.0")))
        self.llm_max_retries = int(preset.get("llm_max_retries", os.getenv("INGEST_MODEL_MAX_RETRIES", "2")))
        self.llm_max_tokens = int(preset.get("llm_max_tokens", os.getenv("SEAI_JSON_MAX_TOKENS", "2048")))
        self.llm_rate_limit_per_minute = int(os.getenv("LLM_RATE_LIMIT_PER_MINUTE", "0"))

        self.embedding_provider = preset.get("embedding_provider") or os.getenv("EMBEDDING_MODEL_PROVIDER", "ollama").lower()
        self.embedding_model = preset.get("embedding_model") or os.getenv("EMBEDDING_MODEL_NAME", "nomic-embed-text")
        self.embedding_base_url = preset.get("embedding_base_url") or os.getenv("EMBEDDING_MODEL_BASE_URL")
        self.embedding_api_key = preset.get("embedding_api_key") or os.getenv("EMBEDDING_MODEL_API_KEY", "")
        self.embedding_rate_limit_per_minute = int(os.getenv("EMBEDDING_RATE_LIMIT_PER_MINUTE", "0"))
        
        self.chunk_size = int(preset.get("chunk_size", 1000))
        self.chunk_overlap = int(preset.get("chunk_overlap", 200))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the global default settings (fallback)."""
    return Settings()


@lru_cache(maxsize=128)
def get_user_settings(user_id: str) -> Settings:
    """Return the active settings for a specific user, falling back to global defaults."""
    from src.repositories.config_presets import get_active
    
    # In some async contexts or if there's no user, fallback to default
    if not user_id:
        return get_settings()
        
    preset = get_active(user_id)
    return Settings(preset)

