import logging
from src.ports.llm import JsonLLM
from src.services.retrieval_engine.domain.seai.json_utils import normalize_plan_json
from src.services.retrieval_engine.domain.seai.models import RetrievalPlan

logger = logging.getLogger(__name__)


class QueryPlanner:
    def __init__(self, json_client: JsonLLM):
        self.json_client = json_client

    def plan(self, query: str) -> RetrievalPlan:
        system = (
            "Plan SEAI retrieval. Return only JSON with keys intent, answer_style, search_queries, "
            "must_find, constraints. Use short search queries optimized for vector search over atoms and episodes."
        )
        human = f"QUESTION:\n{query}"
        try:
            data = normalize_plan_json(self.json_client.invoke_json(system, human))
            plan = RetrievalPlan.model_validate(data)
        except Exception as exc:
            logger.warning("SEAI query planning failed error=%s", exc)
            plan = RetrievalPlan(search_queries=[query])

        if not plan.search_queries:
            plan.search_queries = [query]
        return plan
