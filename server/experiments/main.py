import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from text_cleanup.v2.pipelines.pronoun_resolution import resolve_pronouns
from text_cleanup.v2.pipelines.llm_cleaner import clean_text

from relationship_mapping.extract_entities import extract_entities
from relationship_mapping.extract_relationships_llm import extract_relationships_llm
from relationship_mapping.extract_relationships_spacy import extract_relationships_spacy

INPUT_FILE = os.path.join(BASE_DIR, "input.txt")
OUTPUT_FILE = os.path.join(BASE_DIR, "output.txt")
RELATIONSHIP_FILE = os.path.join(BASE_DIR, "relationship.json")

def main():
    print("=" * 60)
    print(" UNMESS-IT.AI: Full Pipeline (Cleanup + Entity + Relationship) ")
    print("=" * 60)

    if not os.path.exists(INPUT_FILE):
        print(f"Input file not found: {INPUT_FILE}")
        return

    with open(INPUT_FILE, "r") as f:
        raw_text = f.read().strip()
        
    print(f"\n[1] Running Pipeline Step 1: Pronoun Resolution", flush=True)
    resolved_text = resolve_pronouns(raw_text, logit_threshold=5.0)
    
    print(f"\n[2] Running Pipeline Step 2: LLM Chunker", flush=True)
    final_text = clean_text(resolved_text, profile_name="local_deepseek_7b")
    
    with open(OUTPUT_FILE, "w") as f:
        f.write(final_text)
        
    print(f"\nCleaned atomic sentences saved to: {OUTPUT_FILE}")

    print(f"\n[3] Running Pipeline Step 3: Entity & Relationship Extraction")
    lines = [line.strip() for line in final_text.split('\n') if line.strip()]
    
    all_relationships = []
    
    for i, line in enumerate(lines, 1):
        print(f"\n  -> Processing {i}/{len(lines)}: {line}")
        
        # Extract entities
        entities = extract_entities(line, model_profile="local_deepseek_7b")
        if entities:
            print(f"     Entities Found: {entities}")
            
        # Extract relationships (spaCy)
        spacy_rels = extract_relationships_spacy(line)
        
        # Extract relationships (LLM)
        llm_rels = extract_relationships_llm(line, entities=entities, model_profile="local_deepseek_7b")
        
        sentence_data = {
            "sentence": line,
            "entities": entities,
            "relationships_spacy": spacy_rels,
            "relationships_llm": llm_rels
        }
        all_relationships.append(sentence_data)

    with open(RELATIONSHIP_FILE, "w") as f:
        json.dump(all_relationships, f, indent=2)

    total_spacy = sum(len(d["relationships_spacy"]) for d in all_relationships)
    total_llm = sum(len(d["relationships_llm"]) for d in all_relationships)

    print(f"\n============================================================")
    print(f"Pipeline Complete!")
    print(f"Extracted {total_spacy} spaCy relationships and {total_llm} LLM relationships.")
    print(f"Saved to: {RELATIONSHIP_FILE}")
    print(f"============================================================")

if __name__ == "__main__":
    main()
