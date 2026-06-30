from __future__ import annotations

import os

from src.infra.settings import get_user_settings
from src.services.rag.models import SourceWindow


class SourceWindowChain:
    """Split long input into smaller text pieces."""

    def __init__(self, char_limit: int | None = None, overlap: int | None = None) -> None:
        """Use a configurable size limit for each text piece."""
        self.char_limit = char_limit or int(os.getenv("SEAI_SOURCE_CHUNK_CHAR_LIMIT", "2600"))
        self.overlap = overlap if overlap is not None else 0

    def run(self, raw_text: str, user_id: str | None = None) -> list[SourceWindow]:
        """Return text pieces with positions in the original input."""
        char_limit = self.char_limit
        overlap = self.overlap
        if user_id:
            settings = get_user_settings(user_id)
            char_limit = max(1, settings.chunk_size)
            overlap = max(0, min(settings.chunk_overlap, char_limit - 1))

        if len(raw_text) <= char_limit:
            return [{"text": raw_text, "start": 0, "end": len(raw_text)}]

        windows: list[SourceWindow] = []
        start = 0
        while start < len(raw_text):
            end = min(len(raw_text), start + char_limit)
            if end < len(raw_text):
                # Prefer paragraph breaks so one idea is less likely to be split.
                split_at = raw_text.rfind("\n\n", start, end)
                if split_at > start:
                    end = split_at
            windows.append({"text": raw_text[start:end], "start": start, "end": end})
            next_start = end - overlap if end < len(raw_text) else end
            start = next_start if next_start > start else end
        return windows
