from __future__ import annotations


class NoopPreprocessChain:
    def run(self, data: str) -> str:
        return data
