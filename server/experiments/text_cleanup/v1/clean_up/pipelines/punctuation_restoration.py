# ponytail: Fast encoder route.
# Using deepmultilingualpunctuation to safely restore punctuation using Token Classification (Encoder).
import sys
import textwrap

def restore_punctuation(text: str) -> str:
    """
    Pass 0: Punctuation Restoration.
    Uses an encoder-only token classification model to add missing punctuation extremely quickly.
    """
    import torch
    import transformers
    
    # ponytail: Monkeypatch the pipeline initialization to support transformers>=4.35.0
    # deepmultilingualpunctuation uses 'grouped_entities', which was renamed to 'aggregation_strategy'.
    old_init = transformers.TokenClassificationPipeline.__init__
    def new_init(self, *args, **kwargs):
        if 'grouped_entities' in kwargs:
            kwargs['aggregation_strategy'] = 'simple' if kwargs.pop('grouped_entities') else 'none'
        old_init(self, *args, **kwargs)
    transformers.TokenClassificationPipeline.__init__ = new_init

    try:
        from deepmultilingualpunctuation import PunctuationModel
    except ImportError:
        print("[ERROR] deepmultilingualpunctuation not installed.")
        return text

    print("\n[PUNCTUATION] Loading fast encoder model (oliverguhr/fullstop-punctuation-multilang-large)...")
    # ponytail: Instantiating model, this handles all the subword stitching logic for us.
    model = PunctuationModel()
    
    # We still chunk it so we don't blow up the RAM on massive files
    chunks = textwrap.wrap(text, width=2000, break_long_words=False, break_on_hyphens=False)
    
    restored_chunks = []
    print(f"[PUNCTUATION] Processing {len(chunks)} chunks...")
    
    for i, chunk in enumerate(chunks):
        result = model.restore_punctuation(chunk)
        restored_chunks.append(result)
        sys.stdout.write(".")
        sys.stdout.flush()
        
    print("\n[PUNCTUATION] Done.")
    
    # ponytail: Unload model to save memory
    del model
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
        
    return " ".join(restored_chunks)
