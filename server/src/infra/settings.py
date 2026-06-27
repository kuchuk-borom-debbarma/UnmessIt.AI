import os
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env file
load_dotenv(find_dotenv())

class Settings:
    def __init__(self):
        self.llm_model = os.getenv("LLM_MODEL", "ollama:gemma3:1b")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        self.embedding_provider = os.getenv("EMBEDDING_MODEL_PROVIDER", "ollama")
        self.embedding_model = os.getenv("EMBEDDING_MODEL_NAME", "nomic-embed-text")
        self.embedding_base_url = os.getenv("EMBEDDING_MODEL_BASE_URL", "")
        self.embedding_api_key = os.getenv("EMBEDDING_MODEL_API_KEY", "")
