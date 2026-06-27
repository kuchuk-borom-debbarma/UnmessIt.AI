from __future__ import annotations

from src.services.ingest_engine.domain.seai.chains.base import SEAIChain


class LLMEpisodeSummarizer(SEAIChain):
    def __init__(self, client, max_words: int):
        super().__init__()
        self.client = client
        self.max_words = max_words

    def run(self, episode_text: str, fallback: str = "") -> str:
        system = "Write short, neutral, source-grounded SEAI episode summaries. Return only valid JSON, with no markdown."
        human = (
            "Return JSON: {\"summary\":\"...\"}\n"
            f"Keep summary under {self.max_words} words. Do not infer personality or long-term patterns.\n\n"
            f"EPISODE_TEXT:\n{episode_text}"
        )
        try:
            data = self.client.invoke_json(system, human)
            summary = str(data.get("summary", "")).strip()
            return summary or fallback or self._fallback_summary(episode_text)
        except Exception as exc:
            self.logger.warning("seai_summary_failed fallback=true error=%s", exc)
            return fallback or self._fallback_summary(episode_text)

    summarize = run

    @staticmethod
    def _fallback_summary(text: str) -> str:
        return " ".join(text.split())[:240]
