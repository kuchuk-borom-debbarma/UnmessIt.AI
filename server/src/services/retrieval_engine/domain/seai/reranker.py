import json
import logging
from typing import Any
from src.ports.llm import JsonLLM
from src.services.retrieval_engine.domain.seai.models import EvidenceScore, RerankDecision, RetrievalPlan

logger = logging.getLogger(__name__)


class EvidenceReranker:
    def __init__(self, json_client: JsonLLM):
        self.json_client = json_client

    def rerank(
        self,
        query: str,
        plan: RetrievalPlan,
        cards: list[dict[str, Any]],
        round_no: int,
    ) -> RerankDecision:
        if not cards:
            return RerankDecision(missing_aspects=plan.must_find or ["No candidate evidence found."])

        payload = [
            {
                "evidence_id": card["evidence_id"],
                "object_type": card["object_type"],
                "role": card.get("atom_role"),
                "content": card.get("content"),
                "summary": card.get("episode_summary"),
                "evidence": card.get("citable_text"),
                "vector_distance": card.get("distance"),
            }
            for card in cards[:40]
        ]
        system = (
            "Rerank SEAI evidence for answering the question. Select only source-grounded evidence. "
            "Respect entity, subject, and temporal scope in the question. For early/initial/before/after/current/recent questions, "
            "prefer evidence from that scope and reject out-of-scope evidence unless it directly explains contrast. "
            "Prefer direct atom evidence for precise claims, relation atoms for why/how questions, and episodes for necessary context. "
            "Select complementary evidence, not duplicates. "
            "Return only JSON with keys selected_evidence_ids, scores, missing_aspects, "
            "follow_up_queries, enough_evidence. scores items have evidence_id, score, reason. "
            "Use at most 12 selected_evidence_ids and at most 3 follow_up_queries."
        )
        human = json.dumps({
            "question": query,
            "round": round_no,
            "plan": plan.model_dump(),
            "candidate_evidence": payload,
        }, ensure_ascii=False)
        try:
            return RerankDecision.model_validate(self.json_client.invoke_json(system, human))
        except Exception as exc:
            logger.warning("SEAI rerank failed error=%s", exc)
            selected = [card["evidence_id"] for card in cards[:6]]
            return RerankDecision(
                selected_evidence_ids=selected,
                scores=[EvidenceScore(evidence_id=eid, score=0.5) for eid in selected],
                enough_evidence=bool(selected),
            )
