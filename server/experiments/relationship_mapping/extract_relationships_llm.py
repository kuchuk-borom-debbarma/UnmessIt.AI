import json
import urllib.request
import re
from config import RELATIONSHIP_MODELS

def extract_relationships_llm(sentence, entities=None, model_profile="local_deepseek_7b"):
    """
    Extracts Subject-Predicate-Object relationships using a local LLM.
    Optionally takes a list of pre-extracted entities to guide the extraction.
    """
    cfg = RELATIONSHIP_MODELS.get(model_profile, RELATIONSHIP_MODELS["local_deepseek_7b"])
    url = cfg["url"]
    model = cfg["model_name"]
    
    system_prompt = """You are a relationship extraction system. Extract Subject-Predicate-Object relationships from the given sentence.
Output ONLY a raw JSON array of objects with keys: 'head', 'type', 'tail'.
Do not use markdown formatting like ```json.
Example: [{"head": "Sarah", "type": "grabbed", "tail": "wrench"}]"""

    prompt = f"{system_prompt}\n\nSentence: {sentence}\n"
    if entities:
        prompt += f"Identified Entities to focus on: {', '.join(entities)}\n"
    prompt += "Output:"
    
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
            
            clean_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL).strip()
            
            match = re.search(r'\[\s*\{.*?\}\s*\]', clean_text, re.DOTALL)
            if match:
                try:
                    triplets = json.loads(match.group(0))
                    for t in triplets:
                        t["source"] = model
                    return triplets
                except:
                    pass
    except Exception as e:
        print(f"Error calling Ollama for relationships: {e}")
        
    return []
