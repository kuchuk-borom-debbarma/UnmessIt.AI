# /// script
# dependencies = [
#   "transformers",
#   "torch",
#   "deepmultilingualpunctuation",
#   "fastcoref",
#   "spacy",
#   "en-core-web-sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl",
#   "datasets>=2.16.0",
#   "gector",
#   "sentence-transformers",
#   "scikit-learn",
# ]
# ///
import argparse
import json
import re
import sys
import urllib.request
import os

# Add clean_up to path so old modules can be imported
sys.path.append(os.path.join(os.path.dirname(__file__), 'clean_up'))

import config
from cache import load_from_cache, save_to_cache
from pipelines.pronoun_resolution import resolve_pronouns
from pipelines.punctuation_restoration import restore_punctuation
from pipelines.spacy_sanitizer import sanitize_text
from pipelines.gector_grammar import fix_grammar_gector


def llm_query(prompt, raw_chunk):
    data = {
        "model": config.ACTIVE_MODEL,
        "prompt": prompt,
        "stream": True,
        "options": config.LLM_OPTIONS,
    }
    req = urllib.request.Request(
        config.OLLAMA_URL,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    full_response = ""
    print("\n--- LLM PROCESSING STREAM ---\n")
    try:
        with urllib.request.urlopen(req) as response:
            for line in response:
                if line:
                    chunk_data = json.loads(line.decode("utf-8"))
                    text = chunk_data.get("response", "")
                    full_response += text
                    sys.stdout.write(text)
                    sys.stdout.flush()

        # Remove the <think>...</think> block if present
        clean_response = re.sub(
            r"<think>.*?</think>", "", full_response, flags=re.DOTALL
        ).strip()
        print("\n" + "=" * 60)
        return clean_response
    except Exception as e:
        print(f"\n[ERROR] {e}")
        return f"ERROR: {e}"


def main():
    parser = argparse.ArgumentParser(description="UNMESS-IT.AI NLP Pipeline")
    parser.add_argument(
        "input_file", nargs="?", help="Path to input text file (optional)"
    )
    parser.add_argument(
        "--upto",
        type=int,
        choices=[0, 1, 2, 3, 4, 5, 6, 7],
        default=7,
        help="Run pipeline up to this pass (0-7)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print(f" UNMESS-IT.AI : The Modular NLP Pipeline (Running up to Pass {args.upto})")
    print("=" * 60)

    if args.input_file:
        print(f"Reading input from {args.input_file}...")
        try:
            with open(args.input_file, "r") as f:
                raw_text = f.read().strip()
        except Exception as e:
            print(f"Error reading file: {e}")
            return
    else:
        print(
            "Paste your messy text below. Press Ctrl-D (or Ctrl-Z on Windows) when done:"
        )
        raw_text = sys.stdin.read().strip()

    if not raw_text:
        print("No text provided. Exiting.")
        return

    os.makedirs("outputs", exist_ok=True)

    final_doc = raw_text
    chunks = None

    # Pass 0: Punctuation Restoration
    if args.upto >= 0:
        print("\n[0/4] PASS 0: PUNCTUATION RESTORATION")
        cached = load_from_cache("Pass0", raw_text)
        if cached:
            final_doc = cached
        else:
            final_doc = restore_punctuation(raw_text)
            save_to_cache("Pass0", raw_text, final_doc)
        print("  [Pass 0] Punctuation restoration complete.")
        with open("outputs/pipe0_output.txt", "w") as f:
            f.write(final_doc)

    # Pass 1: Spacy Sanitizer (Non-LLM)
    if args.upto >= 1:
        print("\n[1/4] PASS 1: SPACY SANITIZER")
        cached = load_from_cache("Pass1", final_doc)
        if cached:
            final_doc = cached
        else:
            input_text = final_doc
            final_doc = sanitize_text(input_text)
            save_to_cache("Pass1", input_text, final_doc)
        print("  [Pass 1] Sanitizing complete.")
        with open("outputs/pipe1_output.txt", "w") as f:
            f.write(final_doc)

    # Pass 2: Pronoun Resolution
    if args.upto >= 2:
        print("\n[2/4] PASS 2: PRONOUN RESOLUTION")
        cached = load_from_cache("Pass2", final_doc)
        if cached:
            final_doc = cached
        else:
            input_text = final_doc
            final_doc = resolve_pronouns(input_text)
            save_to_cache("Pass2", input_text, final_doc)
        print("  [Pass 2] Coreference resolution complete.")
        with open("outputs/pipe2_output.txt", "w") as f:
            f.write(final_doc)

    # Pass 3: Grammar Smoothing (GECToR)
    if args.upto >= 3:
        print("\n[3/4] PASS 3: GECTOR GRAMMAR SMOOTHER")
        cached = load_from_cache("Pass3", final_doc)
        if cached:
            final_doc = cached
        else:
            input_text = final_doc
            final_doc = fix_grammar_gector(input_text)
            save_to_cache("Pass3", input_text, final_doc)
        print("  [Pass 3] Final rewriting complete.")
        with open("outputs/pipe3_output.txt", "w") as f:
            f.write(final_doc)

    # Pass 4: Atomic Splitter (Deconstruct into smallest propositions)
    if args.upto >= 4:
        from pipelines.atomic_splitter_flan_t5 import split_atomic
        print("\n[4/5] PASS 4: ATOMIC SPLITTER")
        cached = load_from_cache("Pass4", final_doc)
        if cached:
            final_doc = cached
        else:
            input_text = final_doc
            final_doc = split_atomic(input_text)
            save_to_cache("Pass4", input_text, final_doc)
        print("  [Pass 4] Atomic splitting complete.")
        with open("outputs/pipe4_output.txt", "w") as f:
            f.write(final_doc)

    # Pass 5: FLAN-T5 Concise Rewriter
    if args.upto >= 5:
        from pipelines.concise_rewriter_flan_t5 import rewrite_concise_flan_t5
        print("\n[5/6] PASS 5: FLAN-T5 CONCISE REWRITER")
        cached = load_from_cache("Pass5", final_doc)
        if cached:
            final_doc = cached
        else:
            input_text = final_doc
            final_doc = rewrite_concise_flan_t5(input_text)
            save_to_cache("Pass5", input_text, final_doc)
        print("  [Pass 5] Rewriting complete.")
        with open("outputs/pipe5_output.txt", "w") as f:
            f.write(final_doc)
            
    # Pass 6: Semantic Grouper (Phase 2)
    if args.upto >= 6:
        from rewording.semantic_grouper import group_sentences_semantically
        print("\n[6/7] PASS 6: SEMANTIC GROUPER")
        cached = load_from_cache("Pass6", final_doc)
        if cached:
            final_doc = cached
        else:
            input_text = final_doc
            # We use distance_threshold=0.6 as a balanced starting point
            final_doc = group_sentences_semantically(input_text, distance_threshold=0.6)
            save_to_cache("Pass6", input_text, final_doc)
        print("\n  [Pass 6] Semantic grouping complete.")
        os.makedirs("rewording/outputs", exist_ok=True)
        with open("rewording/outputs/pipe6_output.txt", "w") as f:
            f.write(final_doc)

    # Pass 7: Prose Polisher (Phase 2)
    if args.upto >= 7:
        from rewording.prose_polisher import polish_prose_flan_t5
        print("\n[7/7] PASS 7: PROSE POLISHER")
        cached = load_from_cache("Pass7", final_doc)
        if cached:
            final_doc = cached
        else:
            input_text = final_doc
            final_doc = polish_prose_flan_t5(input_text)
            save_to_cache("Pass7", input_text, final_doc)
        print("\n  [Pass 7] Prose polishing complete.")
        os.makedirs("rewording/outputs", exist_ok=True)
        with open("rewording/outputs/pipe7_output.txt", "w") as f:
            f.write(final_doc)

    print("\n\n" + "=" * 60)
    print(f"FINAL TEXT (Stopped after Pass {args.upto})")
    print("=" * 60)
    print(final_doc)
    print("=" * 60)

if __name__ == "__main__":
    main()
