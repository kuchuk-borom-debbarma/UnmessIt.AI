import sys

def rewrite_concise_flan_t5(text: str) -> str:
    """
    Pass 5: FLAN-T5 Concise Rewriter.
    Uses a robust 3-shot prompt to force the model to strip conversational filler
    without hallucinating facts or altering names.
    """
    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except ImportError:
        print("[ERROR] transformers not installed.")
        return text

    print("\n[FLAN-T5 REWRITER] Loading FLAN-T5-large model...")
    tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-large")
    model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-large")

    lines = text.split("\n")
    reconstructed_lines = []
    
    print(f"[FLAN-T5 REWRITER] Processing {len(lines)} sentences...")
    
    for line in lines:
        if not line.strip():
            continue
            
        prompt = (
            "Task: Edit the sentence to be extremely concise. Keep ALL names, lists, and facts exactly the same. Only remove filler adverbs (suddenly, just, actually) and hesitations. NEVER summarize or delete lists of nouns.\n\n"
            "Input: I literally just do not know what he meant by that.\n"
            "Output: I do not know what he meant.\n\n"
            "Input: John says John told Sarah not to go.\n"
            "Output: John says John told Sarah not to go.\n\n"
            "Input: And now suddenly I’m in the car again and I’m just sitting there.\n"
            "Output: I am in the car and I am sitting there.\n\n"
            "Input: Is the delivery person coming, is the cake coming, is the electricity guy coming?\n"
            "Output: Is the delivery person coming, is the cake coming, is the electricity guy coming?\n\n"
            "Input: Who is Sarah?\n"
            "Output: Who is Sarah?\n\n"
            f"Input: {line.strip()}\n"
            "Output:"
        )
            
        inputs = tokenizer(prompt, return_tensors="pt")
        outputs = model.generate(**inputs, max_new_tokens=256)
        
        pruned = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
        
        reconstructed_lines.append(pruned)
        sys.stdout.write(".")
        sys.stdout.flush()

    print("\n[FLAN-T5 REWRITER] Done.")
    
    del model
    del tokenizer
    import gc
    gc.collect()
    try:
        import torch
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
        elif torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass
        
    return "\n".join(reconstructed_lines)
