from .llm_utils import call_llm
import re

def run_atomic_pass(chunk: str, previous_context: str = "", profile_name: str = "local_llama") -> str:
    system_prompt = """You are a strict data parser. Your ONLY job is to break complex, compound sentences into multiple atomic, single-fact sentences.

RULES:
1. Every sentence must contain EXACTLY ONE subject, ONE action, and ONE object.
2. If a sentence has "and", "but", "because", or "so" that introduces a new action or object, split it into completely separate sentences.
3. DO NOT change the original vocabulary. DO NOT summarize. DO NOT use bullet points or lists.
4. Output EACH atomic sentence on a NEW LINE. Do not group them into paragraphs.
5. Output ONLY the atomic sentences. Do NOT output any introductory remarks like "Here are the sentences:" or "text broken into sentences:".

EXAMPLES:
[Input]
I bought a computer but it was broken.
[Output]
I bought a computer.
The computer was broken.

[Input]
He likes to drink water and coke.
[Output]
He likes to drink water.
He likes to drink coke.

[Input]
She washed the car, mowed the lawn, and painted the fence.
[Output]
She washed the car.
She mowed the lawn.
She painted the fence.

[Input]
Dave walked over to help me lift the TV because I couldn't do it alone.
[Output]
Dave walked over to help me lift the TV.
I couldn't do it alone.
"""
    if previous_context:
        user_prompt = f"--- PREVIOUS CONTEXT (DO NOT REPEAT THIS) ---\n{previous_context}\n\n--- TEXT TO MAKE ATOMIC ---\n{chunk}"
    else:
        user_prompt = f"--- TEXT TO SPLIT ---\n{chunk}"
        
    response = call_llm(system_prompt, user_prompt, profile_name)
    return re.sub(r"^(Here is|Here are).*?:?\n*", "", response, flags=re.IGNORECASE).strip()
