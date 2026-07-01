from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any, Awaitable, Callable

AsyncReporter = Callable[[str, dict[str, Any] | None], Awaitable[None]]
SyncReporter = Callable[[str, dict[str, Any] | None], None]

_async_reporter: ContextVar[AsyncReporter | None] = ContextVar("async_progress_reporter", default=None)
_sync_reporter: ContextVar[SyncReporter | None] = ContextVar("sync_progress_reporter", default=None)
_last_llm_rotation_snapshot: ContextVar[dict[str, Any] | None] = ContextVar("last_llm_rotation_snapshot", default=None)
_last_embedding_rotation_snapshot: ContextVar[dict[str, Any] | None] = ContextVar("last_embedding_rotation_snapshot", default=None)


def set_progress_reporters(
    async_reporter: AsyncReporter | None = None,
    sync_reporter: SyncReporter | None = None,
) -> tuple[Token, Token]:
    return _async_reporter.set(async_reporter), _sync_reporter.set(sync_reporter)


def reset_progress_reporters(tokens: tuple[Token, Token]) -> None:
    _async_reporter.reset(tokens[0])
    _sync_reporter.reset(tokens[1])


async def report_progress(message: str, details: dict[str, Any] | None = None) -> None:
    reporter = _async_reporter.get()
    if reporter:
        await reporter(message, details)


def report_progress_sync(message: str, details: dict[str, Any] | None = None) -> None:
    reporter = _sync_reporter.get()
    if reporter:
        reporter(message, details)


def set_last_llm_rotation_snapshot(snapshot: dict[str, Any] | None) -> None:
    _last_llm_rotation_snapshot.set(snapshot)


def get_last_llm_rotation_snapshot() -> dict[str, Any] | None:
    return _last_llm_rotation_snapshot.get()


def set_last_embedding_rotation_snapshot(snapshot: dict[str, Any] | None) -> None:
    _last_embedding_rotation_snapshot.set(snapshot)


def get_last_embedding_rotation_snapshot() -> dict[str, Any] | None:
    return _last_embedding_rotation_snapshot.get()
