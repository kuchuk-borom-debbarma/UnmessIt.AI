from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, TypedDict


class Span(TypedDict):
    start: int
    end: int


class SourceWindow(TypedDict):
    text: str
    start_idx: int
    end_idx: int
    prev_context: str
    next_context: str


EpisodeDraft = dict[str, Any]
AtomDraft = dict[str, Any]
Episode = dict[str, Any]
Atom = dict[str, Any]


@dataclass
class SEAIConfig:
    min_confidence: float = float(os.getenv("SEAI_MIN_CONFIDENCE", "0.4"))
    max_summary_words: int = int(os.getenv("SEAI_MAX_SUMMARY_WORDS", "30"))
    episode_chunk_word_limit: int = int(os.getenv("SEAI_EPISODE_CHUNK_WORD_LIMIT", "450"))
    episode_chunk_char_limit: int = int(os.getenv("SEAI_EPISODE_CHUNK_CHAR_LIMIT", "2600"))
    episode_overlap_chars: int = int(os.getenv("SEAI_EPISODE_OVERLAP_CHARS", "250"))
    enable_fastcoref: bool = os.getenv("SEAI_ENABLE_FASTCOREF", "0") == "1"
