# Factory for dynamically instantiating LLM and ChatModel clients.
# ponytail: Centralizes client initialization so pipes don't have to duplicate Ollama vs OpenAI logic.

import os
from src.infra.langchain.config import (
    DEFAULT_MODEL_NAME,
    DEFAULT_TEMPERATURE,
    DEFAULT_PROVIDER,
    DEFAULT_BASE_URL,
    DEFAULT_API_KEY,
    LLM_RATE_LIMIT_PER_MINUTE,
)
from src.infra.rate_limit import PerMinuteRateLimiter, RateLimitedModel

from typing import Any, List, Optional
from langchain_core.language_models.llms import LLM

class ChatOpenAIAsLLM(LLM):
    chat_model: Any

    def _call(self, prompt: str, stop: Optional[List[str]] = None, **kwargs: Any) -> str:
        res = self.chat_model.invoke(prompt, stop=stop, **kwargs)
        return res.content

    @property
    def _llm_type(self) -> str:
        return "chat_openai_as_llm"


def _json_response_format(base_url: str) -> dict:
    # ponytail: LM Studio rejects OpenAI's old json_object mode; local schema is enough.
    if base_url and ("127.0.0.1:1234" in base_url or "localhost:1234" in base_url):
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "json_response",
                "schema": {"type": "object", "additionalProperties": True},
            },
        }
    return {"type": "json_object"}


_llm_rate_limiter = PerMinuteRateLimiter(LLM_RATE_LIMIT_PER_MINUTE)


def _rate_limited(model):
    return RateLimitedModel(model, _llm_rate_limiter) if LLM_RATE_LIMIT_PER_MINUTE > 0 else model


def get_llm(model_name: str = None, temperature: float = None, format: str = None):
    """
    Returns a standard completion LLM client based on the central provider configuration.
    """
    model = model_name or DEFAULT_MODEL_NAME
    temp = temperature if temperature is not None else DEFAULT_TEMPERATURE
    provider = DEFAULT_PROVIDER

    if provider == "ollama":
        from langchain_ollama import OllamaLLM
        base_url = DEFAULT_BASE_URL or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        ollama_format = "json" if format == "json" else ""
        return _rate_limited(OllamaLLM(model=model, base_url=base_url, temperature=temp, format=ollama_format))
    else:
        # OpenAI or OpenAI-compatible Chat models wrapped as a completion LLM
        # to ensure compatibility with modern hosts (OpenRouter, LM Studio)
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            try:
                from langchain_community.chat_models.openai import ChatOpenAI
            except ImportError:
                raise ImportError(
                    "To use OpenAI-compatible providers, please install the langchain-openai package: "
                    "`pip install langchain-openai`"
                )

        # Set default base URL/key if not specified
        base_url = DEFAULT_BASE_URL
        api_key = DEFAULT_API_KEY or os.getenv("OPENAI_API_KEY") or "dummy-key-for-local-llm"

        kwargs = {}
        if format == "json":
            kwargs["model_kwargs"] = {"response_format": _json_response_format(base_url)}

        chat_model = ChatOpenAI(
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=temp,
            max_tokens=1024,
            **kwargs
        )
        return ChatOpenAIAsLLM(chat_model=_rate_limited(chat_model))


def get_chat_llm(model_name: str = None, temperature: float = None, format: str = None, max_tokens: int = 1024):
    """
    Returns a Chat completion LLM client based on the central provider configuration.
    """
    model = model_name or DEFAULT_MODEL_NAME
    temp = temperature if temperature is not None else DEFAULT_TEMPERATURE
    provider = DEFAULT_PROVIDER

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        base_url = DEFAULT_BASE_URL or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        kwargs = {"format": "json"} if format == "json" else {}
        return _rate_limited(ChatOllama(model=model, base_url=base_url, temperature=temp, **kwargs))
    else:
        # OpenAI or OpenAI-compatible Chat models (LM Studio, OpenRouter, etc.)
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            try:
                from langchain_community.chat_models.openai import ChatOpenAI
            except ImportError:
                raise ImportError(
                    "To use OpenAI-compatible providers, please install the langchain-openai package: "
                    "`pip install langchain-openai`"
                )

        # Set default base URL/key if not specified
        base_url = DEFAULT_BASE_URL
        api_key = DEFAULT_API_KEY or os.getenv("OPENAI_API_KEY") or "dummy-key-for-local-llm"

        kwargs = {}
        if format == "json":
            kwargs["model_kwargs"] = {"response_format": _json_response_format(base_url)}

        return _rate_limited(ChatOpenAI(
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=temp,
            max_tokens=max_tokens,
            **kwargs
        ))
