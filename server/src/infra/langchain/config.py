# Central configuration for the knowledge extraction pipeline.
# ponytail: Single source of truth for LLM model names, temperatures, base URLs, providers, and retry parameters.

import os
try:
    from dotenv import load_dotenv, find_dotenv
except ModuleNotFoundError:
    def find_dotenv():
        return ""

    def load_dotenv(_path=""):
        return False

# Load environment variables from the nearest .env file (searching up from this file's folder)
load_dotenv(find_dotenv())

# The default LLM model to run (e.g. 'llama3.2:latest', 'qwen2.5:3b', 'mistral:latest')
DEFAULT_MODEL_NAME = os.getenv("INGEST_MODEL_NAME", "llama3.2:latest")

# Standard temperature for structured/factual tasks (temperature=0.0 is deterministic and schema-strict)
DEFAULT_TEMPERATURE = float(os.getenv("INGEST_MODEL_TEMPERATURE", "0.0"))

# Maximum validation and parsing retries for structured LLM outputs
DEFAULT_MAX_RETRIES = int(os.getenv("INGEST_MODEL_MAX_RETRIES", "2"))

# The provider type: 'ollama' or 'openai' (which handles OpenAI, LM Studio, OpenRouter, etc.)
DEFAULT_PROVIDER = os.getenv("INGEST_MODEL_PROVIDER", "ollama").lower()

# The base URL of the LLM provider API. If not specified:
# - For 'ollama', defaults to OLLAMA_BASE_URL or 'http://127.0.0.1:11434'
# - For 'openai', defaults to OpenAI's standard endpoints
DEFAULT_BASE_URL = os.getenv("INGEST_MODEL_BASE_URL")

# API key for the provider (required for OpenAI, OpenRouter, etc.)
DEFAULT_API_KEY = os.getenv("INGEST_MODEL_API_KEY", "")

# 0 disables app-side throttling.
LLM_RATE_LIMIT_PER_MINUTE = int(os.getenv("LLM_RATE_LIMIT_PER_MINUTE", "0"))
