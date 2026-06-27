import sys

def polish_prose_flan_t5(text: str) -> str:
    """
    Pass 7: Prose Polisher using FLAN-T5.
    Rewrites the text to fix grammar and make it flow cohesively, 
    preserving the first-person frustrated tone, emotion, and facts.
    """
    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except ImportError:
        print("[ERROR] transformers not installed.")
        return text

    print("\n[PROSE POLISHER] Loading FLAN-T5-large model...")
    tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-large")
    model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-large")

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    polished_paragraphs = []
    
    print(f"[PROSE POLISHER] Processing {len(paragraphs)} paragraphs...")
    
    for i, para in enumerate(paragraphs):
        prompt = (
            "Task: Rewrite the following paragraph to fix grammar and make it flow cohesively. "
            "Crucially, preserve the first-person ('I') frustrated tone, emotion, and facts. "
            "Combine choppy sentences into natural, fluid sentences. "
            "Do NOT turn it into a sterile professional summary. Keep it sounding like a person complaining.\n\n"
            "Input: So I was trying to just finish the thing before lunch. Rohan called. Priya kept sending voice notes. Neha was asking about the electricity bill.\n"
            "Output: So I was just trying to finish the thing before lunch, but then Rohan called, Priya kept sending voice notes, and Neha was asking about the electricity bill!\n\n"
            f"Input: {para}\n"
            "Output:"
        )
            
        inputs = tokenizer(prompt, return_tensors="pt")
        outputs = model.generate(**inputs, max_new_tokens=512)
        
        polished = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
        
        polished_paragraphs.append(polished)
        sys.stdout.write(".")
        sys.stdout.flush()

    print("\n[PROSE POLISHER] Done.")
    
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
        
    return "\n\n".join(polished_paragraphs)
