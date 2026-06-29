from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser

from src.infra.rate_limit import RateLimitedModel, get_limiter
from src.infra.settings import get_user_settings

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
        llm = self.llm or _get_chat_llm(user_id)
        settings = get_user_settings(user_id)
        messages = [SystemMessage(content=system), HumanMessage(content=human)]
        last_error: Exception | None = None
        for attempt in range(1, settings.llm_max_retries + 2):
            content = ""
            try:
                response = llm.invoke(messages)
                content = response.content if hasattr(response, "content") else str(response)
                return JsonOutputParser().parse(content)
            except Exception as exc:
                last_error = exc
                logger.warning("llm_json_parse_failed attempt=%s error=%s", attempt, exc)
                messages = _repair_messages(content, str(exc)) if content.strip() else messages
        raise ValueError(f"LLM returned invalid JSON: {last_error}")

    async def async_invoke_json(self, system: str, human: str, user_id: str) -> dict[str, Any]:
        """Async variant: awaits ainvoke() so the event loop stays free during LLM I/O."""
        llm = self.llm or _get_chat_llm(user_id)
        settings = get_user_settings(user_id)
        messages = [SystemMessage(content=system), HumanMessage(content=human)]
        last_error: Exception | None = None
        for attempt in range(1, settings.llm_max_retries + 2):
            content = ""
            try:
                response = await llm.ainvoke(messages)
                content = response.content if hasattr(response, "content") else str(response)
                return JsonOutputParser().parse(content)
            except Exception as exc:
                last_error = exc
                logger.warning("llm_json_parse_failed_async attempt=%s error=%s", attempt, exc)
                messages = _repair_messages(content, str(exc)) if content.strip() else messages
        raise ValueError(f"LLM returned invalid JSON (async): {last_error}")



@lru_cache(maxsize=1)
def get_json_client() -> JsonLLMClient:
    """Return the process-wide JSON client."""
    return JsonLLMClient()


@lru_cache(maxsize=100)
def _get_chat_llm(user_id: str):
    """Create the provider-specific LangChain chat model lazily, cached per user."""
    settings = get_user_settings(user_id)
    if settings.llm_provider == "ollama":
        from langchain_ollama import ChatOllama

        llm = ChatOllama(
            model=settings.llm_model,
            base_url=settings.llm_base_url or "http://127.0.0.1:11434",
            temperature=settings.llm_temperature,
            format="json",
        )
    else:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key or "dummy-key",
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            model_kwargs={"response_format": _json_response_format(settings.llm_base_url or "")},
        )

    if settings.llm_rate_limit_per_minute > 0:
        # get_limiter returns a singleton so ingest and retrieval share one token bucket.
        return RateLimitedModel(llm, get_limiter(settings.llm_rate_limit_per_minute))
    return llm


def _repair_messages(content: str, error: str) -> list:
    """Prompt used after invalid JSON output."""
    return [
        SystemMessage(content="Repair invalid JSON. Return only valid JSON. No markdown or prose."),
        HumanMessage(content=f"JSON_ERROR:\n{error}\n\nINVALID_JSON:\n{content}"),
    ]


def _json_response_format(base_url: str) -> dict[str, Any]:
    """Use the JSON mode shape supported by local/OpenAI-compatible hosts."""
    if "127.0.0.1:1234" in base_url or "localhost:1234" in base_url:
        return {"type": "json_schema", "json_schema": {"name": "json_response", "schema": {"type": "object"}}}
    return {"type": "json_object"}
