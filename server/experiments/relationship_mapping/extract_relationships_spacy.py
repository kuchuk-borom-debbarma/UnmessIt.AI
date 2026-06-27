import spacy

# Ensure model is loaded once
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")

def extract_relationships_spacy(sentence):
    """
    Extracts Subject-Verb-Object (SVO) relationships using spaCy's dependency parser.
    """
    doc = nlp(sentence)
    triplets = []
    
    for token in doc:
        if token.pos_ == "VERB":
            subjects = [w.text for w in token.lefts if w.dep_ in ("nsubj", "nsubjpass", "csubj", "expl")]
            objects = [w.text for w in token.rights if w.dep_ in ("dobj", "attr", "acomp")]
            
            for right in token.rights:
                if right.dep_ == "prep":
                    objects.extend([w.text for w in right.rights if w.dep_ in ("pobj", "pcomp")])
            
            for subj in subjects:
                for obj in objects:
                    triplets.append({
                        'head': subj, 
                        'type': token.lemma_, 
                        'tail': obj, 
                        'source': 'spacy'
                    })
    return triplets
