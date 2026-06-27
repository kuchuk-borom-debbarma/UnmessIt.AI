import logging
from src.ports.llm import JsonLLM
from src.services.retrieval_engine.domain.seai.models import CitedAnswer

logger = logging.getLogger(__name__)


class StrictAnswerGenerator:
    schema = CitedAnswer

    def __init__(self, json_client: JsonLLM):
        self.json_client = json_client

    def init(self):
        pass

    def close(self):
        pass

    def generate(self, query: str, context: str) -> CitedAnswer:
        system = (
            "Answer using ONLY citable QUOTE BANK blocks in the provided context. "
            "Hints are search hints only; do not answer or cite from hints. "
            "If citable source text does not contain the answer, say the answer is not present in the provided documents. "
            "Every factual claim must have a citation with the UUID shown after QUOTE and an exact quote copied from QUOTE text. "
            "Do not use numeric footnote ids. "
            "Do not use outside knowledge. Return only valid JSON with keys answer_text and citations. "
            "Each citation has statement_id, source_input_id, start_char, end_char, exact_quote."
        )
        human = f"QUESTION:\n{query}\n\nCONTEXT:\n{context}"
        try:
            return CitedAnswer.model_validate(self.json_client.invoke_json(system, human))
        except Exception as exc:
            logger.warning("deterministic answer generation failed error=%s", exc)

        return CitedAnswer(answer_text="No sourced answer found.", citations=[])
