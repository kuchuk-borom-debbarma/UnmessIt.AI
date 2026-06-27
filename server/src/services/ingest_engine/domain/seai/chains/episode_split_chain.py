from __future__ import annotations

from src.services.ingest_engine.domain.seai.chains.base import SEAIChain
from src.services.ingest_engine.domain.seai.models import EpisodeDraft


class LLMEpisodeSplitter(SEAIChain):
    def __init__(self, client):
        super().__init__()
        self.client = client

    def run(self, raw_text: str, prev_context: str = "", next_context: str = "") -> list[EpisodeDraft]:
        system = (
            "You split one raw user input into SEAI episodes. An episode is one meaningful topic, event, "
            "scene, thought, or note. Episodes may have multiple exact evidence quotes if the user leaves "
            "a topic and returns later. Do not rewrite source text. Return only valid JSON, with no markdown."
        )
        context = ""
        if prev_context:
            context += f"PREVIOUS_CONTEXT_FOR_REFERENCE_ONLY:\n{prev_context}\n\n"
        if next_context:
            context += f"NEXT_CONTEXT_FOR_REFERENCE_ONLY:\n{next_context}\n\n"
        human = (
            "Return JSON with this shape:\n"
            '{"episodes":[{"summary":"short neutral source-grounded summary",'
            '"evidence_quotes":["exact substring from CURRENT_CHUNK","another exact substring if needed"]}]}\n\n'
            "Rules:\n"
            "- Use one episode for short focused input.\n"
            "- Use multiple episodes for unrelated mixed input.\n"
            "- Preserve local context so pronouns still make sense.\n"
            "- Each evidence quote must be an exact contiguous substring from CURRENT_CHUNK only.\n"
            "- Use previous/next context only to understand references; do not quote it.\n\n"
            f"{context}"
            f"CURRENT_CHUNK:\n{raw_text}"
        )
        data = self.client.invoke_json(system, human)
        return data.get("episodes", []) if isinstance(data, dict) else []

    split = run
