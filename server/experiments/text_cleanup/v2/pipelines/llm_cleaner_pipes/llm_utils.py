import json
import urllib.request
import re
from config import TEXT_CLEANUP_MODELS, LLM_API_KEY

def call_llm(system_prompt, user_prompt, profile_name="local_llama"):
    # Dynamically fetch the URL and Model for the given profile
    cfg = TEXT_CLEANUP_MODELS.get(profile_name, TEXT_CLEANUP_MODELS["local_llama"])
    url = cfg["url"]
    active_model = cfg["model_name"]
    
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"
        
    # Check if we are using OpenRouter (or standard OpenAI-compatible endpoint)
    if "openrouter.ai" in url or "chat/completions" in url:
        data = {
            "model": active_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode("utf-8"))
                # OpenRouter/OpenAI returns the response in choices[0].message.content
                return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            print(f"  [!] Error calling OpenRouter LLM: {e}")
            return f"[MOCK Cleaned Chunk: {user_prompt[-30:]}...]"
            
    # Default: Ollama format
    else:
        prompt = f"{system_prompt}\n\n{user_prompt}"
        data = {
            "model": active_model,
            "prompt": prompt,
            "stream": False,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode("utf-8"))
                response_text = result.get("response", "").strip()
                # Strip <think> tags for DeepSeek-R1
                clean_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL).strip()
                return clean_text
        except Exception as e:
            print(f"  [!] Error calling Ollama LLM: {e}")
            return f"[MOCK Cleaned Chunk: {user_prompt[-30:]}...]"

def split_text(text, method="word", chunk_size=50):
    if method == "word":
        words = text._split()
        chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
        return chunks
    elif method == "sentence":
        sentences = re.split(r'(?<=[.!?]) +', text.strip())
        chunks = []
        for i in range(0, len(sentences), chunk_size):
            chunks.append(" ".join(sentences[i:i + chunk_size]))
        return chunks
    else:
        raise ValueError("Invalid split method. Use 'word' or 'sentence'.")
