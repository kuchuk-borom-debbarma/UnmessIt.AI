import os
import hashlib

# ponytail: Simple, boring file-based cache.
CACHE_DIR = ".cache_pipeline"

def get_cache_key(pipe_name: str, input_text: str) -> str:
    """
    Generate a deterministic SHA-256 hash for a given pipeline step and its exact input text.
    If the text or the pipe_name changes even slightly, it generates a new hash (cache miss).
    """
    content = f"{pipe_name}|||{input_text}".encode('utf-8')
    return hashlib.sha256(content).hexdigest()

def load_from_cache(pipe_name: str, input_text: str) -> str:
    """
    Return the cached output if it exists, otherwise return None.
    """
    if not os.path.exists(CACHE_DIR):
        return None
    
    key = get_cache_key(pipe_name, input_text)
    cache_path = os.path.join(CACHE_DIR, f"{key}.txt")
    
    if os.path.exists(cache_path):
        print(f"  [CACHE HIT] Loaded {pipe_name} from cache.")
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()
            
    return None

def save_to_cache(pipe_name: str, input_text: str, output_text: str):
    """
    Save the pipeline output to the cache so we don't have to re-run expensive models.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    key = get_cache_key(pipe_name, input_text)
    cache_path = os.path.join(CACHE_DIR, f"{key}.txt")
    
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(output_text)
