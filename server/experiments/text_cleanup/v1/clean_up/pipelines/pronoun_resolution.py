import sys

def resolve_pronouns(text: str) -> str:
    """
    Pass 2: Pronoun Resolution.
    Uses fastcoref via spacy to deterministically resolve he/she/it references.
    """
    try:
        import spacy
        from fastcoref import spacy_component
    except ImportError:
        print("[ERROR] fastcoref or spacy not installed.")
        return text

    print("\n[COREF] Loading fastcoref model (this is highly deterministic)...")
    
    # ponytail: fastcoref hasn't been updated for the newest transformers, which expects `all_tied_weights_keys`.
    # We monkeypatch the underlying FCorefModel init to satisfy it, avoiding a total dependency freeze.
    from fastcoref.coref_models.modeling_fcoref import FCorefModel
    old_init = FCorefModel.__init__
    def new_init(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        self.all_tied_weights_keys = {}
    FCorefModel.__init__ = new_init

    # Zero boilerplate needed.
    nlp = spacy.load("en_core_web_sm")
    nlp.add_pipe("fastcoref")
    
    print("[COREF] Resolving pronouns in text...")
    doc = nlp(text)
    
    # ponytail: fastcoref's internal `doc._.resolved_text` silently fails and returns "" on texts 
    # over ~5000 characters. But the clusters are perfectly accurate. 
    # We do the replacement manually using the cluster offsets.
    resolved = text
    replacements = []
    
    if hasattr(doc._, 'coref_clusters') and doc._.coref_clusters is not None:
        for cluster in doc._.coref_clusters:
            if not cluster: continue
            # The first mention in the cluster is the 'main' noun
            main_mention = text[cluster[0][0]:cluster[0][1]]
            for mention in cluster[1:]:
                mention_text = text[mention[0]:mention[1]].lower()
                
                # ponytail: skip 1st/2nd person pronouns and all reflexives to preserve grammar
                skip_list = {
                    "i", "me", "my", "mine", "myself", 
                    "we", "us", "our", "ours", "ourselves", 
                    "you", "your", "yours", "yourself", "yourselves",
                    "himself", "herself", "itself", "themselves"
                }
                if mention_text in skip_list:
                    continue
                    
                replacement = main_mention
                
                # ponytail: fix possessive declension
                if mention_text in {"his", "her", "hers", "their", "theirs", "its"}:
                    if not replacement.endswith("'s") and not replacement.endswith("'"):
                        replacement += "'" if replacement.endswith("s") else "'s"
                        
                replacements.append((mention[0], mention[1], replacement))
                
        # Sort in reverse order so we don't mess up the character offsets as we replace!
        replacements.sort(key=lambda x: x[0], reverse=True)
        
        for start, end, main_mention in replacements:
            resolved = resolved[:start] + main_mention + resolved[end:]
    
    print("\n[COREF] Done.")
    
    # Clean up memory
    del nlp
    del doc
    import gc
    gc.collect()
    try:
        import torch
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
    except Exception:
        pass
        
    return resolved
