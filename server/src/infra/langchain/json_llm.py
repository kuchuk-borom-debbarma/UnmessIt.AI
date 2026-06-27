from __future__ import annotations

import logging
import os
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser

from src.infra.langchain.config import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_MODEL_NAME,
)
from src.ports.llm import JsonLLM

logger = logging.getLogger(__name__)


class LLMJsonClient(JsonLLM):
    def __init__(
        self,
        llm=None,
        model_name: str = DEFAULT_MODEL_NAME,
        max_retries: int = DEFAULT_MAX_RETRIES,
        max_tokens: int | None = None,
    ):
        self.llm = llm
        self.model_name = model_name
        self.max_retries = max_retries
        self.max_tokens = max_tokens

    def invoke_json(self, system: str, human: str) -> dict[str, Any]:
        if self.llm is None:
            from src.infra.langchain.factory import get_chat_llm
            max_tokens = self.max_tokens or int(os.getenv("SEAI_JSON_MAX_TOKENS", "2048"))
            self.llm = get_chat_llm(model_name=self.model_name, temperature=0, format="json", max_tokens=max_tokens)

        original_messages = [SystemMessage(content=system), HumanMessage(content=human)]
        messages = original_messages
        last_error = None
        for attempt in range(1, self.max_retries + 2):
            content = ""
            try:
                logger.debug(
                    "llm_json_attempt attempt=%s system_chars=%s human_chars=%s",
                    attempt,
                    len(system),
                    len(human),
                )
                response = self.llm.invoke(messages)
                content = response.content if hasattr(response, "content") else str(response)
                logger.debug("llm_json_response attempt=%s response_chars=%s", attempt, len(content))
                return JsonOutputParser().parse(content)
            except Exception as exc:
                last_error = exc
                logger.warning("llm_json_parse_failed attempt=%s error=%s", attempt, exc)
                if content.strip():
                    messages = self._repair_messages(content, str(exc))
                else:
                    messages = original_messages
        raise ValueError(f"SEAI LLM returned invalid JSON: {last_error}")

    @staticmethod
    def _repair_messages(content: str, error: str) -> list:
        return [
            SystemMessage(content=(
                "Repair invalid JSON. Return only valid JSON. No markdown, no prose, no comments. "
                "Preserve all fields and strings exactly unless needed to fix JSON syntax."
            )),
            HumanMessage(content=f"JSON_ERROR:\n{error}\n\nINVALID_JSON:\n{content}"),
        ]
