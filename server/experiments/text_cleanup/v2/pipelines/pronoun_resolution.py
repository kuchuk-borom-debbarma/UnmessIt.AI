# /// script
# dependencies = [
#   "fastcoref",
#   "transformers",
#   "torch",
# ]
# ///

# Monkeypatch for transformers compatibility
from fastcoref.coref_models.modeling_fcoref import FCorefModel
old_init = FCorefModel.__init__
def new_init(self, *args, **kwargs):
    old_init(self, *args, **kwargs)
    self.all_tied_weights_keys = {}
FCorefModel.__init__ = new_init

from fastcoref import FCoref
import gc
import torch

PRONOUNS = {
    "he", "him", "his", "himself",
    "she", "her", "hers", "herself",
    "it", "its", "itself",
    "they", "them", "their", "theirs", "themselves"
}

def resolve_pronouns(text: str, logit_threshold: float = 5.0) -> str:
    print(f"\n[COREF] Loading fastcoref model (Threshold: {logit_threshold})...")
    model = FCoref()
    print("[COREF] Resolving pronouns in text...")
    
    preds = model.predict(texts=[text])
    clusters = preds[0].get_clusters(as_strings=False)
    
    resolved = text
    replacements = []
    
    for cluster in clusters:
        if not cluster: continue
        main_mention_span = cluster[0]
        main_mention = text[main_mention_span[0]:main_mention_span[1]]
        
        for mention_span in cluster[1:]:
            mention_text = text[mention_span[0]:mention_span[1]].lower()
            
            # Skip if it's not a standard 3rd person pronoun
            if mention_text not in PRONOUNS:
                continue
                
            logit = preds[0].get_logit(main_mention_span, mention_span)
            
            if logit >= logit_threshold:
                replacement = main_mention
                # Fix possessive declension
                if mention_text in {"his", "her", "hers", "their", "theirs", "its"}:
                    if not replacement.endswith("'s") and not replacement.endswith("'"):
                        replacement += "'" if replacement.endswith("s") else "'s"
                
                replacements.append((mention_span[0], mention_span[1], replacement))
            else:
                print(f"  [COREF] Skipping '{mention_text}' -> '{main_mention}' (Logit {logit:.2f} < {logit_threshold})")
                
    # Sort in reverse order to replace without messing up offsets
    replacements.sort(key=lambda x: x[0], reverse=True)
    
    for start, end, replacement in replacements:
        resolved = resolved[:start] + replacement + resolved[end:]
        
    print(f"[COREF] Made {len(replacements)} high-certainty replacements.")
    
    # Cleanup memory
    del model
    del preds
    gc.collect()
    try:
        # if torch.backends.mps.is_available():
        #    torch.mps.empty_cache()
        pass
    except Exception:
        pass
        
    return resolved
