from __future__ import annotations

import json

from src.services.ingest_engine.domain.seai.chains.base import SEAIChain
from src.services.ingest_engine.domain.seai.models import AtomDraft
from src.services.ingest_engine.domain.seai.utils.evidence import extract_atom_list


class LLMAtomVerifier(SEAIChain):
    def __init__(self, client):
        super().__init__()
        self.client = client

    def run(self, episode_text: str, atoms: list[AtomDraft]) -> list[AtomDraft]:
        if not atoms:
            return []
        system = (
            "Verify SEAI atoms against one episode. Reject atoms that invent information, remove uncertainty, "
            "overgeneralize, make personality judgments, or cite evidence not present in the episode. "
            "Keep only grounded useful atoms. Return only valid JSON, with no markdown."
        )
        human = (
            "Return JSON: {\"atoms\":[kept atom objects with same fields]}.\n\n"
            f"EPISODE_TEXT:\n{episode_text}\n\n"
            f"ATOMS:\n{json.dumps({'atoms': atoms}, ensure_ascii=False)}"
        )
        data = self.client.invoke_json(system, human)
        return extract_atom_list(data)

    verify = run
