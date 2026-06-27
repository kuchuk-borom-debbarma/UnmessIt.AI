from __future__ import annotations

from src.services.ingest_engine.domain.seai.chains.base import SEAIChain


class LLMEpisodeVerifier(SEAIChain):
    def __init__(self, client):
        super().__init__()
        self.client = client

    def run(self, episode_text: str, summary: str, fallback: str = "") -> str:
        if not summary.strip():
            return fallback
        system = (
            "Verify an SEAI episode summary. If the summary is fully supported by EPISODE_TEXT, keep it. "
            "If it invents names, roles, motives, events, or swaps entities, rewrite it to only say what the text supports. "
            "Return only valid JSON with key summary."
        )
        human = (
            "Return JSON: {\"summary\":\"grounded summary\"}\n\n"
            f"EPISODE_TEXT:\n{episode_text}\n\n"
            f"SUMMARY:\n{summary}"
        )
        try:
            data = self.client.invoke_json(system, human)
            verified = str(data.get("summary", "")).strip()
            return verified or fallback or self._fallback_summary(episode_text)
        except Exception as exc:
            self.logger.warning("seai_episode_summary_verify_failed fallback=true error=%s", exc)
            return fallback or self._fallback_summary(episode_text)

    verify_summary = run

    @staticmethod
    def _fallback_summary(text: str) -> str:
        return " ".join(text.split())[:240]
