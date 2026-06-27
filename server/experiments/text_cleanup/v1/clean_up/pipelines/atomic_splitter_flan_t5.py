import sys
import re

def split_atomic(text: str) -> str:
    """
    Pass 4: Atomic Splitter.
    Uses FLAN-T5-large to break complex, compound sentences into the smallest
    standalone atomic units without losing any meaning.
    """
    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except ImportError:
        print("[ERROR] transformers not installed.")
        return text

    print("\n[ATOMIC SPLITTER] Loading FLAN-T5-large model...")
    tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-large")
    model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-large")

    raw_sentences = re.split(r'([.?!])', text)
    
    chunks = []
    for i in range(0, len(raw_sentences) - 1, 2):
        sentence = raw_sentences[i].strip() + raw_sentences[i+1]
        if sentence.strip():
            chunks.append(sentence)
            
    if len(raw_sentences) % 2 != 0 and raw_sentences[-1].strip():
        chunks.append(raw_sentences[-1].strip())

    reconstructed_chunks = []
    print(f"[ATOMIC SPLITTER] Processing {len(chunks)} sentences for atomic splitting...")
    
    for chunk in chunks:
        # We use a few-shot prompt to teach FLAN-T5 to split without deleting details
        prompt = (
            "Split the complex sentence into multiple simple, standalone sentences. DO NOT delete any details or meaning.\n"
            "Original: The dog ran into the house and then ate his food because he was hungry.\n"
            "Split: The dog ran into the house. The dog ate his food. The dog was hungry.\n"
            f"Original: {chunk}\n"
            "Split:"
        )
            
        inputs = tokenizer(prompt, return_tensors="pt")
        outputs = model.generate(**inputs, max_new_tokens=256)
        split_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # ponytail: FLAN-T5 sometimes hallucinates by continuing the few-shot pattern.
        # We aggressively cut off anything that looks like a continuation of the prompt loop.
        split_text = split_text._split("Original:")[0].strip()
        split_text = split_text._split("\n")[0].strip()
        
        reconstructed_chunks.append(split_text)
        sys.stdout.write(".")
        sys.stdout.flush()

    print("\n[ATOMIC SPLITTER] Done.")
    
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
    # Format with newlines
    final_text = "\n".join(reconstructed_chunks)
    final_text = final_text.replace(". ", ".\n")
    return final_text
