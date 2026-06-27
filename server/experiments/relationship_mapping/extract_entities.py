import os
import json
import urllib.request
import re
from config import RELATIONSHIP_MODELS

def extract_entities(sentence, model_profile="local_deepseek_7b"):
    """
    Extracts core entities from a sentence using a local LLM.
    """
    cfg = RELATIONSHIP_MODELS.get(model_profile, RELATIONSHIP_MODELS["local_deepseek_7b"])
    url = cfg["url"]
    model = cfg["model_name"]
    
    system_prompt = """You are an entity extraction system. Extract the core entities (people, places, objects, concepts) from the given sentence.
Output ONLY a raw JSON list of strings. Do not use markdown formatting like ```json.
Example: ["Sarah", "giant wrench", "toolbox"]"""
    
    prompt = f"{system_prompt}\n\nSentence: {sentence}\nOutput:"
    
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            response_text = result.get("response", "")
            
            # Strip <think> tags for models like deepseek-r1
            clean_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL).strip()
            
            match = re.search(r'\[\s*.*?\s*\]', clean_text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except:
                    pass
    except Exception as e:
        print(f"Error calling Ollama for entities: {e}")
    
    return []
