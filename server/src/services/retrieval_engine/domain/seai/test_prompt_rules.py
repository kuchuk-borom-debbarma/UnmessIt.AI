from pathlib import Path

from src.services.retrieval_engine.domain.seai.answer_generator import StrictAnswerGenerator
from src.services.retrieval_engine.domain.seai.planner import QueryPlanner
from src.services.retrieval_engine.domain.seai.reranker import EvidenceReranker


class CaptureJsonClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def invoke_json(self, system, human):
        self.calls.append((system, human))
        return self.response


def test_prompt_rules_doc_exists():
    root = Path(__file__).resolve().parents[5]
    text = (root / "docs" / "rules" / "prompt_rules.md").read_text()

    assert "General Standard" in text
    assert "Domain Neutrality" in text
    assert "user input can be any kind of text" in text
    assert "Output Contracts" in text
    assert "Grounding" in text
    assert "Scope Control" in text
    assert "Applying These Rules Here" in text


def test_planner_prompt_names_scope_terms():
    client = CaptureJsonClient({"search_queries": ["Eren early worldview"]})

    QueryPlanner(client).plan("What was Eren's early worldview?")

    system, _ = client.calls[0]
    assert "early" in system
    assert "Do not broaden a scoped question" in system


def test_reranker_prompt_prefers_scoped_evidence():
    client = CaptureJsonClient({"selected_evidence_ids": [], "enough_evidence": False})

    EvidenceReranker(client).rerank(
        "What was Eren's early worldview?",
        type("Plan", (), {"must_find": [], "model_dump": lambda self: {}})(),
        [{"evidence_id": "episode:1", "object_type": "episode", "episode_summary": "later evidence"}],
        1,
    )

    system, _ = client.calls[0]
    assert "Respect entity, subject, and temporal scope" in system
    assert "early/initial/before/after/current/recent" in system
    assert "Select complementary evidence" in system


def test_answer_prompt_requires_complete_supported_synthesis():
    client = CaptureJsonClient({"answer_text": "No sourced answer found.", "citations": []})

    StrictAnswerGenerator(client).generate("What was Eren's early worldview?", "QUOTE BANK:\n")

    system, _ = client.calls[0]
    assert "synthesize the complete supported picture" in system
    assert "Respect the question scope" in system
