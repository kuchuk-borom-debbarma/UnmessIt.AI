from __future__ import annotations

from typing import Any, Protocol


class JsonLLM(Protocol):
    def invoke_json(self, system: str, human: str) -> dict[str, Any]:
        ...

