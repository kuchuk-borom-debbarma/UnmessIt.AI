from .llm_utils import call_llm
import re

def run_concise_pass(chunk: str, previous_context: str = "", profile_name: str = "local_llama") -> str:
    base_prompt = """You are a strict data-cleaning assistant. Your ONLY job is to remove conversational fluff, filler words, and subjective emotional commentary from the text.
    
RULES:
1. Remove filler words (e.g., "like", "you know", "honestly", "basically", "so yeah").
2. Remove subjective emotional commentary (e.g., "which was super annoying", "it was so disgusting").
3. Preserve ALL specific facts, numbers, actions, and objects perfectly.
4. Output ONLY the cleaned text, formatted as standard paragraphs. Do not use bullet points or lists."""

    context_rule = "\n5. If PREVIOUS CONTEXT is provided, DO NOT REPEAT IT IN YOUR OUTPUT. It is ONLY provided so you know what the current text is referring to."
    
    examples = """
EXAMPLES:
[Input]
honestly the pipe was basically cracked completely and it was so annoying but we drove over there in her car and the guy at the hardware store gave us like fifty pvc pipes
[Output]
The pipe was completely cracked. We drove over there in her car, and the guy at the hardware store gave us fifty PVC pipes.
"""
    system_prompt = base_prompt + (context_rule if previous_context else "") + examples
    
    if previous_context:
        user_prompt = f"--- PREVIOUS CONTEXT (DO NOT REPEAT THIS) ---\n{previous_context}\n\n--- TEXT TO CLEAN ---\n{chunk}"
    else:
        user_prompt = f"Text to clean:\n{chunk}"
        
    response = call_llm(system_prompt, user_prompt, profile_name)
    return re.sub(r"^(Here is|Here are).*?:?\n*", "", response, flags=re.IGNORECASE).strip()
