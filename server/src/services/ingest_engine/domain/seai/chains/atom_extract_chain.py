from __future__ import annotations

from src.services.ingest_engine.domain.seai.chains.base import SEAIChain
from src.services.ingest_engine.domain.seai.models import AtomDraft
from src.services.ingest_engine.domain.seai.utils.evidence import extract_atom_list


class LLMAtomExtractor(SEAIChain):
    def __init__(self, client):
        super().__init__()
        self.client = client

    def run(self, episode_text: str) -> list[AtomDraft]:
        system = (
            "You extract SEAI memory atoms from one episode. Extract only source-supported statements. "
            "Every atom must be a complete standalone claim with enough context to be understood without the episode. "
            "Create direct atoms for directly expressed facts/events/states/preferences. Create relation atoms "
            "for local relationships like cause, sequence, contrast, dependency, example, or result. "
            "Do not infer personality, hidden motives, long-term patterns, or global conclusions. "
            "Preserve uncertainty. Return only valid JSON, with no markdown."
        )
        human = (
            "Return JSON with this shape:\n"
            '{"atoms":[{"content":"small standalone statement","evidence_quotes":["exact source quote"],'
            '"atom_role":"direct","annotations":["event","belief"],"confidence":0.9}]}\n\n'
            "Rules:\n"
            "- atom_role must be direct or relation.\n"
            "- evidence_quotes must be exact substrings from EPISODE_TEXT.\n"
            "- Do not write label-like fragments such as 'Early Eren thinks in simple terms'. Instead write the full claim.\n"
            "- Prefer useful generic annotations: topic, entity, time, place, event, action, belief, preference, "
            "goal, motivation, cause, consequence, contrast, relationship, status, uncertainty, plan, problem, decision, evidence.\n\n"
            f"EPISODE_TEXT:\n{episode_text}"
        )
        data = self.client.invoke_json(system, human)
        return extract_atom_list(data)

    extract = run
