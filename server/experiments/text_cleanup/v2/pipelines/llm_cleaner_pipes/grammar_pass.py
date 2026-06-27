from .llm_utils import call_llm
import re

def run_grammar_pass(chunk: str, previous_context: str = "", profile_name: str = "local_llama") -> str:
    system_prompt = """You are an expert copy editor. Your ONLY job is to fix grammatical errors, remove stuttering, and restore proper punctuation in the text provided.
    
RULES:
1. Do NOT summarize or shorten the text.
2. Do NOT change the speaker's original intent or tone.
3. Fix run-on sentences by breaking them apart with periods.
4. Output ONLY the fixed text, with no introductory or concluding remarks.

EXAMPLES:
[Input]
so um i went to the the store and i bought milk and bread and then i went home
[Output]
So, I went to the store, and I bought milk and bread. Then, I went home.
"""
    
    if previous_context:
        user_prompt = f"--- PREVIOUS CONTEXT (Do NOT edit or repeat this) ---\n{previous_context}\n\n--- TEXT TO EDIT ---\n{chunk}"
    else:
        user_prompt = f"--- TEXT TO EDIT ---\n{chunk}"
        
    response = call_llm(system_prompt, user_prompt, profile_name)
    return re.sub(r"^(Here is|Here are).*?:?\n*", "", response, flags=re.IGNORECASE).strip()
