from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI

from src.infra.rate_limit import RateLimitedModel, get_limiter
from src.infra.settings import Settings, get_user_setting_candidates, get_user_settings
from src.infra.progress import report_progress, set_last_llm_rotation_snapshot, report_progress_sync

logger = logging.getLogger(__name__)


class JsonLLMClient:
    """Thin JSON-only LLM wrapper used by chains.

    Chains provide prompts and expect dictionaries. Provider setup, JSON parse
    retries, and repair prompts stay here so chains stay small.
    """

    def __init__(self, llm=None) -> None:
        """Allow tests to inject a fake `llm` without touching LangChain."""
        self.llm = llm

    def invoke_json(self, system: str, human: str, user_id: str) -> dict[str, Any]:
        """Invoke the chat model and parse a JSON object."""
        if self.llm:
            return self._invoke_with_settings(self.llm, get_user_settings(user_id), system, human)

        errors = []
        candidates = list(get_user_setting_candidates(user_id))

        for index, settings in enumerate(candidates, start=1):
            report_progress_sync(
                f"LLM config {index}/{len(candidates)} selected: {settings.preset_name}",
                {"preset_id": settings.preset_id, "preset_name": settings.preset_name, "attempt": index, "total": len(candidates)},
            )
            try:
                result = self._invoke_with_settings(_get_chat_llm(settings.llm_cache_key()), settings, system, human)
                set_last_llm_rotation_snapshot(settings.rotation_snapshot())
                report_progress_sync(
                    f"LLM config succeeded: {settings.preset_name}",
                    {"preset_id": settings.preset_id, "preset_name": settings.preset_name},
                )
                return result
            except Exception as exc:
                errors.append(f"{settings.preset_name}: {exc}")
                logger.warning("llm_rotation_preset_failed preset=%s error=%s", settings.preset_name, exc)
                report_progress_sync(
                    f"LLM config failed: {settings.preset_name}",
                    {"preset_id": settings.preset_id, "preset_name": settings.preset_name, "error": str(exc)[:500]},
                )
        report_progress_sync("All LLM configs failed.", {"errors": errors})
        raise ValueError("All LLM configs failed: " + "; ".join(errors))

    def _invoke_with_settings(self, llm, settings: Settings, system: str, human: str) -> dict[str, Any]:
        messages = [SystemMessage(content=system), HumanMessage(content=human)]
        last_error: Exception | None = None
        for attempt in range(1, settings.llm_max_retries + 2):
            content = ""
            try:
                try:
                    import sniffio
                    sniffio.current_async_library_cvar.set(None)
                except Exception:
                    pass
                response = llm.invoke(messages)
                content = response.content if hasattr(response, "content") else str(response)
                return JsonOutputParser().parse(content)
            except Exception as exc:
                last_error = exc
                logger.warning("llm_json_parse_failed attempt=%s error=%s", attempt, exc)
                if not content.strip():
                    raise ValueError(f"LLM API error: {exc}") from exc
                messages = _repair_messages(content, str(exc))
        raise ValueError(f"LLM returned invalid JSON: {last_error}")

    async def async_invoke_json(self, system: str, human: str, user_id: str) -> dict[str, Any]:
        """Async variant: awaits ainvoke() so the event loop stays free during LLM I/O."""
        if self.llm:
            return await self._async_invoke_with_settings(self.llm, get_user_settings(user_id), system, human)

        errors = []
        candidates = list(get_user_setting_candidates(user_id))

        for index, settings in enumerate(candidates, start=1):
            await report_progress(
                f"LLM config {index}/{len(candidates)} selected: {settings.preset_name}",
                {"preset_id": settings.preset_id, "preset_name": settings.preset_name, "attempt": index, "total": len(candidates)},
            )
            try:
                result = await self._async_invoke_with_settings(_get_chat_llm(settings.llm_cache_key()), settings, system, human)
                set_last_llm_rotation_snapshot(settings.rotation_snapshot())
                await report_progress(
                    f"LLM config succeeded: {settings.preset_name}",
                    {"preset_id": settings.preset_id, "preset_name": settings.preset_name},
                )
                return result
            except Exception as exc:
                errors.append(f"{settings.preset_name}: {exc}")
                logger.warning("llm_rotation_preset_failed preset=%s error=%s", settings.preset_name, exc)
                await report_progress(
                    f"LLM config failed: {settings.preset_name}",
                    {"preset_id": settings.preset_id, "preset_name": settings.preset_name, "error": str(exc)[:500]},
                )
                if index < len(candidates):
                    await report_progress(f"Trying next LLM config after {settings.preset_name} failed.")
        await report_progress("All LLM configs failed.", {"errors": errors})
        raise ValueError("All LLM configs failed: " + "; ".join(errors))

    async def _async_invoke_with_settings(self, llm, settings: Settings, system: str, human: str) -> dict[str, Any]:
        messages = [SystemMessage(content=system), HumanMessage(content=human)]
        last_error: Exception | None = None
        for attempt in range(1, settings.llm_max_retries + 2):
            content = ""
            try:
                await report_progress(
                    f"Calling language model {settings.llm_model} (attempt {attempt}/{settings.llm_max_retries + 1})",
                    {"preset_id": settings.preset_id, "model": settings.llm_model, "attempt": attempt},
                )
                response = await llm.ainvoke(messages)
                content = response.content if hasattr(response, "content") else str(response)
                return JsonOutputParser().parse(content)
            except Exception as exc:
                last_error = exc
                logger.warning("llm_json_parse_failed_async attempt=%s error=%s", attempt, exc)
                if not content.strip():
                    # Network or API error (e.g. rate limit), don't hammer the same API. Rotate immediately.
                    raise ValueError(f"LLM API error (async): {exc}") from exc
                messages = _repair_messages(content, str(exc))
        raise ValueError(f"LLM returned invalid JSON (async): {last_error}")

@lru_cache(maxsize=1)
def get_json_client() -> JsonLLMClient:
    """Return the process-wide JSON client."""
    return JsonLLMClient()


@lru_cache(maxsize=100)
def _get_chat_llm(cache_key: tuple):
    """Create the provider-specific LangChain chat model lazily."""
    (
        _preset_id,
        _provider,
        model,
        base_url,
        api_key,
        temperature,
        _max_retries,
        max_tokens,
        rate_limit,
    ) = cache_key

    kwargs = {
        "model": model,
        "base_url": base_url,
        "api_key": api_key or "dummy-key",
        "temperature": temperature,
        "model_kwargs": {"response_format": _json_response_format(base_url or "")},
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    llm = ChatOpenAI(**kwargs)

    if rate_limit > 0:
        # get_limiter returns a singleton so ingest and retrieval share one token bucket.
        return RateLimitedModel(llm, get_limiter(rate_limit))
    return llm


def _repair_messages(content: str, error: str) -> list:
    """Prompt used after invalid JSON output."""
    return [
        SystemMessage(content="Repair invalid JSON. Return only valid JSON. No markdown or prose."),
        HumanMessage(content=f"JSON_ERROR:\n{error}\n\nINVALID_JSON:\n{content}"),
    ]


def _json_response_format(base_url: str) -> dict[str, Any]:
    """Use the JSON mode shape supported by local/OpenAI-compatible hosts."""
    if any(host in base_url for host in ("127.0.0.1:1234", "localhost:1234", "host.docker.internal:1234")):
        return {"type": "json_schema", "json_schema": {"name": "json_response", "schema": {"type": "object"}}}
    return {"type": "json_object"}
