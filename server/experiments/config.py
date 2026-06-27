import os
from dotenv import load_dotenv

# Load from .env file
load_dotenv()

# Only keep secrets in .env
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

# Per-model configuration map for Text Cleanup
TEXT_CLEANUP_MODELS = {
    "local_deepseek_7b": {
        "url": "http://localhost:11434/api/generate",
        "model_name": "deepseek-r1:7b",
        "split_method": "word",
        "chunk_size": 100,
        "context_words": 50
    },
    "local_llama": {
        "url": "http://localhost:11434/api/generate",
        "model_name": "llama3.1:8b",
        "split_method": "word",
        "chunk_size": 100,
        "context_words": 50
    },
    "local_deepseek": {
        "url": "http://localhost:11434/api/generate",
        "model_name": "deepseek-r1:14b",
        "split_method": "word",
        "chunk_size": 50,
        "context_words": 25
    },
    "or_deepseek": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "model_name": "deepseek/deepseek-v4-flash",
        "split_method": "word",
        "chunk_size": 200,
        "context_words": 100
    },
    "or_haiku": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "model_name": "anthropic/claude-3-haiku",
        "split_method": "word",
        "chunk_size": 200,
        "context_words": 100
    }
}

# Per-model configuration map for Relationship and Entity Extraction
RELATIONSHIP_MODELS = {
    "local_deepseek_7b": {
        "url": "http://localhost:11434/api/generate",
        "model_name": "deepseek-r1:7b"
    },
    "local_qwen_7b": {
        "url": "http://localhost:11434/api/generate",
        "model_name": "qwen2.5:7b"
    }
}
