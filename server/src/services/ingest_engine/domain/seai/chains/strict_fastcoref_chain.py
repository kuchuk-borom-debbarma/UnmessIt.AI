from __future__ import annotations

import re

from src.services.ingest_engine.domain.seai.chains.base import SEAIChain

import transformers

if not hasattr(transformers.PreTrainedModel, "all_tied_weights_keys"):
    transformers.PreTrainedModel.all_tied_weights_keys = property(lambda self: {})

_PRONOUNS = {
    "he", "him", "his", "she", "her", "hers", "it", "its", "they", "them", "their", "theirs",
}


class NoopPreprocessor:
    def run(self, text: str) -> str:
        return text

    process = run


class StrictFastcorefPreprocessor(SEAIChain):
    def __init__(self):
        super().__init__()
        self.model = None

    def run(self, text: str) -> str:
        if not text.strip():
            return text
        if self.model is None:
            from fastcoref import FCoref
            self.model = FCoref(device="cpu")

        predictions = self.model.predict(texts=[text])
        clusters = predictions[0].get_clusters(as_strings=False)
        replacements = []
        for cluster in clusters or []:
            head = self._first_non_pronoun(text, cluster)
            if not head:
                continue
            head_start, head_end = head
            head_text = text[head_start:head_end]
            for start, end in cluster:
                mention = text[start:end]
                if start > head_start and self._is_pronoun(mention):
                    replacements.append((start, end, head_text))

        resolved = text
        for start, end, replacement in sorted(replacements, key=lambda item: item[0], reverse=True):
            resolved = resolved[:start] + replacement + resolved[end:]
        if replacements:
            self.logger.info("seai_fastcoref_resolved replacement_count=%s", len(replacements))
        return resolved

    process = run

    @staticmethod
    def _first_non_pronoun(text: str, cluster: list[tuple[int, int]]) -> tuple[int, int] | None:
        for start, end in sorted(cluster):
            if not StrictFastcorefPreprocessor._is_pronoun(text[start:end]):
                return start, end
        return None

    @staticmethod
    def _is_pronoun(text: str) -> bool:
        return re.sub(r"[^A-Za-z]", "", text).lower() in _PRONOUNS
