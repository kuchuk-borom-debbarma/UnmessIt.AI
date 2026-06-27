import re
import torch
import os


def fix_grammar_gector(text):
    print("  [Pass 3] Initializing GECToR...")
    try:
        from gector import GECToR, load_verb_dict, predict
        from transformers import AutoTokenizer
    except ImportError:
        print("\n[ERROR] gector not installed. Run: pip install gector")
        return text

    if not os.path.exists("roberta_1_gector.th") or not os.path.exists("data/verb-form-vocab.txt"):
        print("\n[ERROR] Missing GECToR resources.")
        print("--- GECTOR SETUP REQUIRED ---")
        print("1. Please ensure 'roberta_1_gector.th' is in the v1 folder.")
        print("2. Please ensure 'data/verb-form-vocab.txt' exists.")
        print("3. Please ensure 'data/output_vocabulary/' exists.")
        print("-----------------------------\n")
        return text

    try:
        # Safely patch torch.load to always load on CPU
        _original_load = torch.load
        def _safe_load(f, *args, **kwargs):
            kwargs['map_location'] = torch.device('cpu')
            return _original_load(f, *args, **kwargs)
        torch.load = _safe_load

        model = GECToR.from_official_pretrained(
            pretrained_model_name_or_path="roberta_1_gector.th",
            special_tokens_fix=1,
            transformer_model="roberta-base",
            vocab_path="data/output_vocabulary"
        )
        
        # Restore immediately
        torch.load = _original_load

        model.config.max_length = 80  # Fix missing attribute bug in gector library
        model.eval()
        tokenizer = AutoTokenizer.from_pretrained("roberta-base")
        encode, decode = load_verb_dict("data/verb-form-vocab.txt")
    except Exception as e:
        print(f"\n[ERROR] Failed to load GECToR model: {e}")
        return text

    # Chunk by sentence so GECToR can process them optimally
    raw_sentences = re.split(r'([.?!])', text)
    sentences = [s.strip() for s in raw_sentences if s.strip() and not re.match(r'^[.?!]+$', s.strip())]
    punctuation = [s for s in raw_sentences if re.match(r'^[.?!]+$', s.strip())]
    if len(punctuation) < len(sentences):
        punctuation.append("")

    try:
        # predict() takes a list of strings
        # Restrict to 1 iteration and set keep_confidence to prevent hallucinated grammatical insertions
        reconstructed_chunks = predict(model, tokenizer, sentences, encode, decode, batch_size=16, n_iteration=1, keep_confidence=0.5)
    except Exception as e:
        print(f"\n[ERROR] GECToR prediction failed: {e}")
        reconstructed_chunks = sentences
            
    final_text = ""
    for i, chunk in enumerate(reconstructed_chunks):
        final_text += chunk
        if i < len(punctuation):
            final_text += punctuation[i] + " "
            
    return final_text.strip()
