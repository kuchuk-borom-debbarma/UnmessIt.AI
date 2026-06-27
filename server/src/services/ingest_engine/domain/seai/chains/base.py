from __future__ import annotations

import logging
from typing import Any, Protocol


class Chain(Protocol):
    def run(self, *args: Any, **kwargs: Any) -> Any:
        ...


class SEAIChain:
    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger(self.__class__.__module__)
