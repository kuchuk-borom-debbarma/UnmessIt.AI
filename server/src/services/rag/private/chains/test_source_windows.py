from __future__ import annotations

from src.services.rag.private.chains.source_windows import SourceWindowChain


def test_source_windows_use_configured_overlap():
    windows = SourceWindowChain(char_limit=5, overlap=2).run("abcdefghijkl")

    assert windows == [
        {"text": "abcde", "start": 0, "end": 5},
        {"text": "defgh", "start": 3, "end": 8},
        {"text": "ghijk", "start": 6, "end": 11},
        {"text": "jkl", "start": 9, "end": 12},
    ]
