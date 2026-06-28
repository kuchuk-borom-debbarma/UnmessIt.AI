from __future__ import annotations

import os

from src.services.rag.models import SourceWindow


class SourceWindowChain:
    """Split long input into smaller text pieces."""

    def __init__(self, char_limit: int | None = None) -> None:
        """Use a configurable size limit for each text piece."""
        self.char_limit = char_limit or int(os.getenv("SEAI_SOURCE_CHUNK_CHAR_LIMIT", "2600"))

    def run(self, raw_text: str) -> list[SourceWindow]:
        """Return text pieces with positions in the original input."""
        if len(raw_text) <= self.char_limit:
            return [{"text": raw_text, "start": 0, "end": len(raw_text)}]

        windows: list[SourceWindow] = []
        start = 0
        while start < len(raw_text):
            end = min(len(raw_text), start + self.char_limit)
            if end < len(raw_text):
                # Prefer paragraph breaks so one idea is less likely to be split.
                split_at = raw_text.rfind("\n\n", start, end)
                if split_at > start:
                    end = split_at
            windows.append({"text": raw_text[start:end], "start": start, "end": end})
            start = end
        return windows
