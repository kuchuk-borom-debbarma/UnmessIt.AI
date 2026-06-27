# ---------------------------------------------------------
# UNMESS-IT.AI : Pipeline Configuration
# ---------------------------------------------------------

# Available Ollama Models on your machine
MODELS = {
    "granite": "granite4.1:3b",
    "llama": "llama3.1",
}

# --- ACTIVE CONFIGURATION ---

# Swap the string below to easily change the Pass 1 LLM model
ACTIVE_MODEL = MODELS["llama"]

# Ollama Connection
OLLAMA_URL = "http://localhost:11434/api/generate"

# LLM Sampling Parameters (Deterministic for Semantic Chunking)
LLM_OPTIONS = {"temperature": 0.0, "top_p": 1.0, "top_k": -1, "num_predict": 8192}
