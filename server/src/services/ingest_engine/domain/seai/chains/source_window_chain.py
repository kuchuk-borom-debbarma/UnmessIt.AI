from __future__ import annotations

from src.services.ingest_engine.domain.seai.chains.windowing.context_adder import ContextAdder
from src.services.ingest_engine.domain.seai.chains.windowing.tiered_split import TieredSplitter
from src.services.ingest_engine.domain.seai.chains.base import SEAIChain
from src.services.ingest_engine.domain.seai.models import SEAIConfig, SourceWindow


class SourceWindowChain(SEAIChain):
    def __init__(self, config: SEAIConfig):
        super().__init__()
        self.config = config

    def run(self, raw_text: str) -> list[SourceWindow]:
        splitter = TieredSplitter(
            word_limit=self.config.episode_chunk_word_limit,
            char_limit=self.config.episode_chunk_char_limit,
        )
        chunks = splitter.chain(raw_text)
        if not chunks:
            return [{
                "text": raw_text,
                "start_idx": 0,
                "end_idx": len(raw_text),
                "prev_context": "",
                "next_context": "",
            }]

        cursor = 0
        for chunk in chunks:
            idx = raw_text.find(chunk.text, cursor)
            if idx == -1:
                idx = raw_text.find(chunk.text)
            if idx != -1:
                chunk.start_idx = idx
                chunk.end_idx = idx + len(chunk.text)
                cursor = chunk.end_idx

        chunks = ContextAdder(overlap_size=self.config.episode_overlap_chars).chain(chunks)
        windows = []
        for chunk in chunks:
            windows.append({
                "text": chunk.text,
                "start_idx": chunk.start_idx,
                "end_idx": chunk.end_idx,
                "prev_context": (chunk.prev_context or {}).get("text", ""),
                "next_context": (chunk.next_context or {}).get("text", ""),
            })
        return windows

    windows = run
