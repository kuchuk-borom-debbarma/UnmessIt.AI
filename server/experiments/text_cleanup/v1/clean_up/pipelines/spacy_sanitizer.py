import re

def sanitize_text(text: str) -> str:
    """
    Pass 1: Sanitizer (Non-LLM)
    Uses regular expressions to strip out conversational filler words and fix multiple spaces.
    """
    print("\n[SANITIZER] Removing filler words...")
    
    # Common conversational fillers
    fillers = [
        r'\bum\b', r'\buh\b', r'\blike\b', r'\byou know\b', 
        r'\bhonestly\b', r'\bbasically\b', r'\bliterally\b',
        r'\bI mean\b', r'\banyway\b', r'\bso yeah\b', r'\byeah so\b'
    ]
    
    sanitized = text
    for filler in fillers:
        # Remove the filler word (case insensitive) and optional trailing commas/spaces
        sanitized = re.sub(filler + r',?\s*', '', sanitized, flags=re.IGNORECASE)
        
    # Clean up multiple spaces and dangling commas
    sanitized = re.sub(r'\s+', ' ', sanitized)
    sanitized = re.sub(r' ,', ',', sanitized)
    sanitized = re.sub(r'\s+\.', '.', sanitized)
    sanitized = re.sub(r'^\s*([A-Z])', r'\1', sanitized) # capitalize first letter if needed, or just let pass 0 handle it
    
    # ponytail: sometimes the regex leaves behind double punctuation or capitalized words mid-sentence, 
    # but the grammar pass (GECToR) will fix those!
    
    print("[SANITIZER] Done.")
    return sanitized.strip()
