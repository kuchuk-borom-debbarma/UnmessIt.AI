from .llm_cleaner_pipes.llm_utils import split_text
from .llm_cleaner_pipes.grammar_pass import run_grammar_pass
from .llm_cleaner_pipes.concise_pass import run_concise_pass
from .llm_cleaner_pipes.atomic_pass import run_atomic_pass
from config import TEXT_CLEANUP_MODELS

def clean_text(text: str, profile_name: str = "local_llama") -> str:
    cfg = TEXT_CLEANUP_MODELS.get(profile_name, TEXT_CLEANUP_MODELS["local_llama"])
    split_method = cfg["split_method"]
    chunk_size = cfg["chunk_size"]
    context_words = cfg["context_words"]
    active_model = cfg["model_name"]

    print(f"\n[LLM] Starting Modular LLM Cleanup pipeline (Profile: {profile_name} | Model: {active_model})")

    chunks = split_text(text, method=split_method, chunk_size=chunk_size)
    print(f"[LLM] Split into {len(chunks)} chunks using '{split_method}' method (Size: {chunk_size})")
    
    cleaned_chunks = []
    previous_context = ""

    for i, chunk in enumerate(chunks):
        print(f"\n[LLM] Processing Chunk {i + 1}/{len(chunks)}")
        
        if i == 0:
            context = ""
        else:
            prev_words = previous_context.split()
            context = " ".join(prev_words[-context_words:]) if len(prev_words) > context_words else previous_context
            
        print(f"  -> Pass 1: Grammar & Punctuation")
        grammar_text = run_grammar_pass(chunk, context, profile_name)
        
        print(f"  -> Pass 2: Fluff Removal (Concise)")
        concise_text = run_concise_pass(grammar_text, context, profile_name)
        
        print(f"  -> Pass 3: Atomic Sentences")
        atomic_text = run_atomic_pass(concise_text, "", profile_name)
        
        cleaned_chunks.append(atomic_text)
        
        # Update the context for the next chunk
        previous_context = atomic_text
        
    return "\n".join(cleaned_chunks)
