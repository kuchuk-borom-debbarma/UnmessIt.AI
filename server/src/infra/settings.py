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
    def __init__(self) -> None:
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        self.llm_provider = os.getenv("INGEST_MODEL_PROVIDER", "ollama").lower()
        self.llm_model = os.getenv("INGEST_MODEL_NAME", "llama3.2:latest")
        self.llm_base_url = os.getenv("INGEST_MODEL_BASE_URL")
        self.llm_api_key = os.getenv("INGEST_MODEL_API_KEY", "")
        self.llm_temperature = float(os.getenv("INGEST_MODEL_TEMPERATURE", "0.0"))
        self.llm_max_retries = int(os.getenv("INGEST_MODEL_MAX_RETRIES", "2"))
        self.llm_max_tokens = int(os.getenv("SEAI_JSON_MAX_TOKENS", "2048"))
        self.llm_rate_limit_per_minute = int(os.getenv("LLM_RATE_LIMIT_PER_MINUTE", "0"))

        self.embedding_provider = os.getenv("EMBEDDING_MODEL_PROVIDER", "ollama").lower()
        self.embedding_model = os.getenv("EMBEDDING_MODEL_NAME", "nomic-embed-text")
        self.embedding_base_url = os.getenv("EMBEDDING_MODEL_BASE_URL", "")
        self.embedding_api_key = os.getenv("EMBEDDING_MODEL_API_KEY", "")
        self.embedding_rate_limit_per_minute = int(os.getenv("EMBEDDING_RATE_LIMIT_PER_MINUTE", "0"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
