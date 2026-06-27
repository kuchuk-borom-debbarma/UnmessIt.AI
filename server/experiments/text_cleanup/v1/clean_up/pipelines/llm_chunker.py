import re

# Small for SLMs. If using a strong model, this can be huge and the model can determine the splits.
MIN_CHUNK_SIZE = 500

# Hard ceiling to prevent infinite EXTEND loops on massive run-on sentences.
MAX_CHUNK_SIZE = 2000

PAST_WINDOW = 100
FUTURE_WINDOW = 100

def chunk_text(text: str, llm_query_fn) -> list[str]:
    """
    Its job is to split text where one meaning ends.
    We want the chunks to be as small as possible because small SLMs have limited context capacity and struggle with tangled topics.
    
    ALGORITHM: PAST-CURRENT-FUTURE SEMANTIC CHUNKING
    -------------------------------------------------
    Since the input has zero punctuation (no periods, no newlines), we cannot use regex. 
    We rely on the LLM to find the semantic boundaries (where a thought ends).
    
    1. Define window sizes (e.g., PAST=50 chars, MIN_CURRENT=500 chars, FUTURE=50 chars, MAX_CURRENT=2000 chars).
    2. Extract the three strings based on our current cursor position in the raw text.
    3. Construct the prompt:
       [PAST CONTEXT]: <text before cursor>
       [CURRENT CHUNK]: <text at cursor>
       [FUTURE PEEK]: <text after current chunk>
       
    4. Task the LLM: 
       "Find the exact word/character where the final complete thought in [CURRENT CHUNK] ends. 
       If the thought bleeds into [FUTURE PEEK], reply with 'EXTEND'. Do NOT rewrite the text, only output the matching exact phrase or index."
       
    5. Evaluation & Edge Case Defenses:
       - Extend Loop: If LLM replies "EXTEND", we increase CURRENT.
       - Hard Ceiling: If CURRENT >= MAX_CURRENT, we force a naive split to avoid OOM on run-on sentences.
       - Anti-Hallucination: LLM outputs an index or exact substring match, NEVER the rewritten text.
       - Edge of Cliff: If PAST or FUTURE are empty (start/end of doc), proceed normally. If FUTURE is empty, LLM must finalize.
       - Tiny Remnant: If the text remaining after a split is smaller than MIN_CHUNK_SIZE, forcibly append it to the current chunk rather than stranding it.
       - Success: We save the bounded chunk, and move the cursor forward to that exact index.
       
    ponytail: currently using naive word-aware chunking to fit context limits.
    Upgrade path: Implement the loop above using config.ACTIVE_MODEL.
    """
    chunks = []
    cursor = 0
    text_len = len(text)
    
    def safe_fallback_cut(chunk: str) -> int:
        """Finds the last space in the chunk to avoid cutting words in half."""
        idx = chunk.rfind(' ')
        return idx if idx != -1 else len(chunk)

    while cursor < text_len:
        current_window = MIN_CHUNK_SIZE
        
        while True:
            # 1. Slice strings
            past_start = max(0, cursor - PAST_WINDOW)
            past_context = text[past_start:cursor]
            
            current_end = min(text_len, cursor + current_window)
            current_chunk = text[cursor:current_end]
            
            future_end = min(text_len, current_end + FUTURE_WINDOW)
            future_peek = text[current_end:future_end]
            
            # Edge of cliff
            if not future_peek:
                chunks.append(current_chunk)
                cursor = current_end
                break
                
            # 2. Prompt LLM
            prompt = f"""
You are a semantic boundary detector. Your job is to find the exact character index where the final complete thought in [CURRENT CHUNK] ends.
If the thought bleeds into [FUTURE PEEK], you must reply exactly with 'EXTEND'.
Do NOT rewrite the text. Do NOT add markdown or conversational text. ONLY output the index (an integer) or 'EXTEND'.

[PAST CONTEXT]:
{past_context}

[CURRENT CHUNK]:
{current_chunk}

[FUTURE PEEK]:
{future_peek}

Answer (integer index or EXTEND):
"""
            
            print(f"\n[CHUNKER] Analyzing chunk at cursor {cursor} (window size {current_window})...")
            response = llm_query_fn(prompt, current_chunk).strip()
            
            if "EXTEND" in response.upper():
                if current_window >= MAX_CHUNK_SIZE:
                    print("[CHUNKER] WARNING: Hit MAX_CHUNK_SIZE ceiling. Forcing safe word split.")
                    cut_idx = safe_fallback_cut(current_chunk)
                    chunks.append(current_chunk[:cut_idx])
                    cursor += cut_idx
                    break
                else:
                    print("[CHUNKER] Extending window...")
                    current_window += int(MIN_CHUNK_SIZE / 2) # extend gradually
                    continue
            else:
                # Try to parse index
                try:
                    # Extract the first integer found in response
                    match = re.search(r'\d+', response)
                    if match:
                        cut_idx = int(match.group(0))
                        # Anti-hallucination bounds check
                        if cut_idx <= 0 or cut_idx > len(current_chunk):
                            print(f"[CHUNKER] LLM gave invalid index {cut_idx}. Forcing safe word split.")
                            cut_idx = safe_fallback_cut(current_chunk)
                    else:
                        print(f"[CHUNKER] LLM response '{response}' had no index. Forcing safe word split.")
                        cut_idx = safe_fallback_cut(current_chunk)
                        
                    final_chunk = current_chunk[:cut_idx]
                    
                    # Tiny remnant trap
                    remaining_in_doc = text_len - (cursor + cut_idx)
                    if 0 < remaining_in_doc < MIN_CHUNK_SIZE:
                        print("[CHUNKER] Catching tiny remnant.")
                        final_chunk = text[cursor:]
                        chunks.append(final_chunk)
                        cursor = text_len
                        break
                        
                    chunks.append(final_chunk)
                    cursor += cut_idx
                    break
                    
                except Exception as e:
                    print(f"[CHUNKER] Parsing failed: {e}. Forcing safe word split.")
                    cut_idx = safe_fallback_cut(current_chunk)
                    chunks.append(current_chunk[:cut_idx])
                    cursor += cut_idx
                    break

    return chunks
