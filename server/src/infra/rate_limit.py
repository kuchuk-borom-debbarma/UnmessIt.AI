from __future__ import annotations

import time
from collections import deque
from functools import lru_cache
from threading import Lock
from typing import Callable


# ponytail: one shared limiter per RPM value; callers must not construct their own.
@lru_cache(maxsize=8)
def get_limiter(calls_per_minute: int) -> "PerMinuteRateLimiter":
    """Return the process-wide rate limiter for a given RPM cap.

    Using a singleton means concurrent ingest + retrieval requests share one
    token bucket and the configured cap is the real global cap, not per-caller.
    """
    return PerMinuteRateLimiter(calls_per_minute)


class PerMinuteRateLimiter:
    def __init__(
        self,
        calls_per_minute: int,
        *,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.calls_per_minute = calls_per_minute
        self.monotonic = monotonic
        self.sleep = sleep
        self._calls = deque()
        self._lock = Lock()

    def wait(self) -> None:
        if self.calls_per_minute <= 0:
            return

        while True:
            with self._lock:
                now = self.monotonic()
                while self._calls and now - self._calls[0] >= 60:
                    self._calls.popleft()
                if len(self._calls) < self.calls_per_minute:
                    self._calls.append(now)
                    return
                delay = 60 - (now - self._calls[0])
            self.sleep(max(delay, 0))


class RateLimitedModel:
    def __init__(self, model, limiter: PerMinuteRateLimiter) -> None:
        self.model = model
        self.limiter = limiter

    def invoke(self, *args, **kwargs):
        self.limiter.wait()
        return self.model.invoke(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.model, name)


class RateLimitedEmbeddingFunction:
    def __init__(self, embedding_function, limiter: PerMinuteRateLimiter) -> None:
        self.embedding_function = embedding_function
        self.limiter = limiter

    def __call__(self, input):
        self.limiter.wait()
        return self.embedding_function(input)

    def __getattr__(self, name):
        return getattr(self.embedding_function, name)
