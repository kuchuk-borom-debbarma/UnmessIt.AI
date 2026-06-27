import sys
import re

def rewrite_concise(text: str) -> str:
    """
    Pass 1 & 3: Concise Rewriter / Grammar Smoother.
    Uses the local LLM to rewrite sentences to be clear, standard, and concise.
    Removes filler words, hesitations, and unnecessary fluff while fixing grammar.
    """
    from main import llm_query

    print("\n[REWRITING] Chunking text by sentence...")
    # ponytail: Since Pass 0 gave us real punctuation, we can safely chunk by sentence!
    # No more arbitrary 500-char cuts.
    raw_sentences = re.split(r'([.?!])', text)
    
    chunks = []
    # re.split with capture group keeps the delimiters, so we stitch them back: ["hello", ".", "world", "!"]
    for i in range(0, len(raw_sentences) - 1, 2):
        sentence = raw_sentences[i].strip() + raw_sentences[i+1]
        if sentence.strip():
            chunks.append(sentence)
    
    # Catch any leftover string with no punctuation at the very end
    if len(raw_sentences) % 2 != 0 and raw_sentences[-1].strip():
        chunks.append(raw_sentences[-1].strip())

    reconstructed_chunks = []
    print(f"[REWRITING] Processing {len(chunks)} sentences for concise rewording...")
    
    for i, chunk in enumerate(chunks):
        # ponytail: Delete FLAN-T5-large and use the local LLM!
        prompt = (
            "Rewrite the following sentence to be clear, standard, and concise. "
            "Remove all filler words, hesitations, and unnecessary fluff. "
            "Fix any grammatical errors, including improper pronoun declensions. "
            "Keep the original meaning. Output ONLY the corrected sentence, nothing else.\n\n"
            f"Sentence: '{chunk}'\n\nOutput:"
        )
            
        sys.stdout.write(f"\n[Sentence {i+1}/{len(chunks)}] ")
        sys.stdout.flush()
        
        reconstructed_text = llm_query(prompt, chunk)
        
        # Clean up any prompt leakage
        reconstructed_text = reconstructed_text.replace("Output:", "").replace("Sentence:", "").strip()
        reconstructed_text = reconstructed_text.strip("\"'")
        
        reconstructed_chunks.append(reconstructed_text)

    print("\n[REWRITING] Done.")
    return " ".join(reconstructed_chunks)
