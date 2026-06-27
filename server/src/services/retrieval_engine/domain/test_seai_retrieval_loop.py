import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from src.infra.langchain.json_llm import LLMJsonClient
from src.services.retrieval_engine.domain.DeterministicRetrievalService import (
    Citation,
    CitedAnswer,
    DeterministicRetrievalService,
    RerankDecision,
    RetrievalPlan,
    _normalize_query,
    _normalize_plan_json,
)


RAW = "Amy punched a man because he behaved badly."
EPISODE = {
    "id": "episode_1",
    "raw_input_id": "raw_1",
    "text": RAW,
    "summary": "Amy punched a man because he behaved badly.",
    "spans": [{"start": 0, "end": len(RAW)}],
    "raw_text": RAW,
}
ATOM = {
    "id": "atom_1",
    "raw_input_id": "raw_1",
    "episode_id": "episode_1",
    "content": "The man's bad behavior caused Amy to punch him.",
    "atom_role": "relation",
    "annotations": ["cause"],
    "confidence": 0.9,
    "evidence_spans": [{"start": 0, "end": len(RAW)}],
    "evidence_text": RAW,
    "raw_text": RAW,
}


class FakeVectorStore:
    def __init__(self, hits_by_query):
        self.hits_by_query = hits_by_query

    def search(self, query, top_k=5):
        return self.hits_by_query.get(query, self.hits_by_query.get("*", []))


class FakeRepo:
    def __init__(self, episodes=None, atoms=None):
        self.episodes = {episode["id"]: episode for episode in (episodes or [EPISODE])}
        self.atoms = {atom["id"]: atom for atom in (atoms or [ATOM])}

    def get_atoms_by_ids(self, atom_ids):
        return [self.atoms[atom_id] for atom_id in atom_ids if atom_id in self.atoms]

    def get_episodes_by_ids(self, episode_ids):
        return [self.episodes[episode_id] for episode_id in episode_ids if episode_id in self.episodes]

    def get_atoms_by_episode_ids(self, episode_ids):
        return [atom for atom in self.atoms.values() if atom["episode_id"] in episode_ids]

    def search_episodes_by_terms(self, terms, limit=12):
        lowered = [term.lower() for term in terms]
        result = []
        for episode in self.episodes.values():
            haystack = f"{episode.get('summary', '')} {episode.get('text', '')} {episode.get('raw_text', '')}".lower()
            if any(term in haystack for term in lowered):
                result.append(episode)
        return result[:limit]

    def search_atoms_by_terms(self, terms, limit=16):
        lowered = [term.lower() for term in terms]
        result = []
        for atom in self.atoms.values():
            haystack = f"{atom.get('content', '')} {' '.join(atom.get('annotations', []))} {atom.get('raw_text', '')}".lower()
            if any(term in haystack for term in lowered):
                result.append(atom)
        return result[:limit]


class FakePlanner:
    def __init__(self, queries=None):
        self.queries = queries or ["initial"]

    def plan(self, query):
        return RetrievalPlan(
            intent="why_question",
            answer_style="concise",
            search_queries=self.queries,
            must_find=["cause"],
            constraints=["source-bound"],
        )


class FakeReranker:
    def __init__(self, decisions):
        self.decisions = decisions
        self.calls = []

    def rerank(self, query, plan, cards, round_no):
        self.calls.append((round_no, [card["evidence_id"] for card in cards]))
        return self.decisions[min(round_no - 1, len(self.decisions) - 1)]


class FakeAnswerGenerator:
    def __init__(self, answers):
        self.answers = list(answers)
        self.contexts = []

    def init(self):
        pass

    def close(self):
        pass

    def generate(self, query, context):
        self.contexts.append(context)
        if self.answers:
            return self.answers.pop(0)
        return CitedAnswer(answer_text="No sourced answer found.", citations=[])


def episode_hit():
    return {
        "object_id": "episode_1",
        "metadata": {"object_type": "episode", "episode_id": "episode_1", "object_id": "episode_1"},
        "distance": 0.4,
    }


def episode_hit_for(episode_id, distance=0.4):
    return {
        "object_id": episode_id,
        "metadata": {"object_type": "episode", "episode_id": episode_id, "object_id": episode_id},
        "distance": distance,
    }


def atom_hit():
    return {
        "object_id": "atom_1",
        "metadata": {"object_type": "atom", "atom_id": "atom_1", "episode_id": "episode_1"},
        "distance": 0.1,
    }


class TestSEAIRetrievalLoop(unittest.TestCase):
    def test_invoke_json_repairs_invalid_json(self):
        class RepairLLM:
            def __init__(self):
                self.calls = 0

            def invoke(self, messages):
                self.calls += 1
                content = '{"ok": true "items": []}' if self.calls == 1 else '{"ok": true, "items": []}'
                return type("Response", (), {"content": content})()

        data = LLMJsonClient(llm=RepairLLM(), max_retries=1).invoke_json("system", "human")

        self.assertTrue(data["ok"])

    def test_planner_normalizes_dict_constraints(self):
        data = _normalize_plan_json({
            "search_queries": "Eren worldview",
            "must_find": {"entity": "Eren", "time": "childhood"},
            "constraints": {"entity_types": ["person"], "answer_types": ["text"]},
        })

        plan = RetrievalPlan.model_validate(data)

        self.assertEqual(plan.search_queries, ["Eren worldview"])
        self.assertIn("entity: Eren", plan.must_find)
        self.assertIn("entity_types: ['person']", plan.constraints)

    def test_numbered_query_is_normalized(self):
        self.assertEqual(_normalize_query("21. What was Eren's early worldview?"), "What was Eren's early worldview?")

    def test_multi_pass_followup_finds_relation_atom(self):
        vector_store = FakeVectorStore({
            "*": [episode_hit()],
            "bad behavior cause": [atom_hit()],
        })
        reranker = FakeReranker([
            RerankDecision(
                selected_evidence_ids=["episode:episode_1"],
                follow_up_queries=["bad behavior cause"],
                enough_evidence=False,
            ),
            RerankDecision(selected_evidence_ids=["atom:atom_1"], enough_evidence=True),
        ])
        answerer = FakeAnswerGenerator([
            CitedAnswer(
                answer_text="Amy punched the man because he behaved badly.",
                citations=[Citation(statement_id="atom_1", exact_quote=RAW)],
            )
        ])
        service = DeterministicRetrievalService(
            vector_store,
            FakeRepo(),
            query_planner=FakePlanner(["initial"]),
            evidence_reranker=reranker,
            answer_generator=answerer,
        )

        result = service.query("Why did Amy punch the man?")

        self.assertEqual(result["answer"], "Amy punched the man because he behaved badly.")
        self.assertEqual(len(result["retrieval_trace"]["rounds"]), 2)
        self.assertIn("atom:atom_1", result["retrieval_trace"]["selected_evidence_ids"])

    def test_context_budget_uses_span_snippets_not_full_episode(self):
        huge_raw = "x" * 20000
        episode = {
            **EPISODE,
            "id": "huge_episode",
            "text": huge_raw,
            "summary": "Huge episode.",
            "spans": [{"start": 0, "end": len(huge_raw)}],
            "raw_text": huge_raw,
        }
        vector_store = FakeVectorStore({
            "*": [{
                "object_id": "huge_episode",
                "metadata": {"object_type": "episode", "episode_id": "huge_episode", "object_id": "huge_episode"},
                "distance": 0.1,
            }]
        })
        answerer = FakeAnswerGenerator([CitedAnswer(answer_text="No sourced answer found.", citations=[])])
        service = DeterministicRetrievalService(
            vector_store,
            FakeRepo(episodes=[episode], atoms=[]),
            query_planner=FakePlanner(["huge"]),
            evidence_reranker=FakeReranker([
                RerankDecision(selected_evidence_ids=["episode:huge_episode"], enough_evidence=True)
            ]),
            answer_generator=answerer,
        )

        service.query("What is in the huge episode?")

        self.assertLessEqual(max(len(context) for context in answerer.contexts), 9000)
        self.assertNotIn("x" * 10000, answerer.contexts[0])

    def test_unknown_and_duplicate_reranker_ids_are_ignored(self):
        answerer = FakeAnswerGenerator([
            CitedAnswer(
                answer_text="Amy punched a man because he behaved badly.",
                citations=[Citation(statement_id="atom_1", exact_quote=RAW)],
            )
        ])
        service = DeterministicRetrievalService(
            FakeVectorStore({"*": [atom_hit()]}),
            FakeRepo(),
            query_planner=FakePlanner(),
            evidence_reranker=FakeReranker([
                RerankDecision(
                    selected_evidence_ids=["missing", "atom:atom_1", "atom:atom_1"],
                    enough_evidence=True,
                )
            ]),
            answer_generator=answerer,
        )

        result = service.query("Why?")

        self.assertEqual(result["retrieval_trace"]["selected_evidence_ids"], ["atom:atom_1"])

    def test_bad_citation_triggers_one_retry(self):
        answerer = FakeAnswerGenerator([
            CitedAnswer(
                answer_text="Bad answer.",
                citations=[Citation(statement_id="atom_1", exact_quote="not in source")],
            ),
            CitedAnswer(
                answer_text="Amy punched a man because he behaved badly.",
                citations=[Citation(statement_id="atom_1", exact_quote=RAW)],
            ),
        ])
        service = DeterministicRetrievalService(
            FakeVectorStore({"*": [atom_hit()]}),
            FakeRepo(),
            query_planner=FakePlanner(),
            evidence_reranker=FakeReranker([
                RerankDecision(selected_evidence_ids=["atom:atom_1"], enough_evidence=True)
            ]),
            answer_generator=answerer,
        )

        result = service.query("Why did Amy punch the man?")

        self.assertTrue(result["retrieval_trace"]["answer_retry"])
        self.assertEqual(result["answer"], "Amy punched a man because he behaved badly.")
        self.assertEqual(len(answerer.contexts), 2)

    def test_broad_query_adds_extra_episode_context(self):
        early = {
            **EPISODE,
            "id": "episode_early",
            "summary": "Eren wanted freedom early.",
            "raw_text": "Eren wanted freedom early.",
            "text": "Eren wanted freedom early.",
            "spans": [{"start": 0, "end": len("Eren wanted freedom early.")}],
        }
        fear = {
            **EPISODE,
            "id": "episode_fear",
            "summary": "Eren hated living trapped inside walls.",
            "raw_text": "Eren hated living trapped inside walls.",
            "text": "Eren hated living trapped inside walls.",
            "spans": [{"start": 0, "end": len("Eren hated living trapped inside walls.")}],
        }
        unrelated = {
            **EPISODE,
            "id": "episode_unrelated",
            "summary": "Amy bought coffee.",
            "raw_text": "Amy bought coffee.",
            "text": "Amy bought coffee.",
            "spans": [{"start": 0, "end": len("Amy bought coffee.")}],
        }
        answerer = FakeAnswerGenerator([
            CitedAnswer(
                answer_text="Eren's early worldview centered on freedom and feeling trapped.",
                citations=[Citation(statement_id="episode_early", exact_quote="Eren wanted freedom early.")],
            )
        ])
        service = DeterministicRetrievalService(
            FakeVectorStore({"*": [
                episode_hit_for("episode_early", 0.1),
                episode_hit_for("episode_fear", 0.2),
                episode_hit_for("episode_unrelated", 0.3),
                atom_hit(),
            ]}),
            FakeRepo(episodes=[EPISODE, early, fear, unrelated]),
            query_planner=FakePlanner(["Eren early worldview"]),
            evidence_reranker=FakeReranker([
                RerankDecision(
                    selected_evidence_ids=["episode:episode_early"],
                    missing_aspects=["broader worldview evidence"],
                    enough_evidence=True,
                )
            ]),
            answer_generator=answerer,
        )

        result = service.query("What was Eren's early worldview?")

        self.assertIn("[QUOTE episode_fear]", answerer.contexts[0])
        self.assertNotIn("[QUOTE episode_unrelated]", answerer.contexts[0])
        self.assertIn("QUOTE:", answerer.contexts[0])
        self.assertTrue(result["retrieval_trace"]["context_broadened"])

    def test_broad_query_uses_lexical_sweep(self):
        eren_raw = "At the beginning, Eren sees the walls as a prison."
        eren_episode = {
            **EPISODE,
            "id": "episode_eren",
            "summary": "Eren sees the walls as a prison.",
            "text": eren_raw,
            "raw_text": eren_raw,
            "spans": [{"start": 0, "end": len(eren_raw)}],
        }
        answerer = FakeAnswerGenerator([
            CitedAnswer(
                answer_text="Eren viewed the walls as a prison.",
                citations=[Citation(statement_id="episode_eren", exact_quote=eren_raw)],
            )
        ])
        service = DeterministicRetrievalService(
            FakeVectorStore({"*": [episode_hit()]}),
            FakeRepo(episodes=[EPISODE, eren_episode]),
            query_planner=FakePlanner(["Eren worldview walls"]),
            evidence_reranker=FakeReranker([
                RerankDecision(selected_evidence_ids=["episode:episode_1"], missing_aspects=["Eren"], enough_evidence=True)
            ]),
            answer_generator=answerer,
        )

        result = service.query("21. What was Eren's early worldview?")

        self.assertGreater(result["retrieval_trace"]["lexical_sweep_count"], 0)
        self.assertIn("[QUOTE episode_eren]", answerer.contexts[0])

    def test_retrieval_docs_cover_core_contract(self):
        root = Path(__file__).resolve().parents[4]
        retrieval_doc = (root / "docs" / "SEAI_RETRIEVAL_FLOW.md").read_text()
        indexing_doc = (root / "docs" / "SEAI_INDEXING_FLOW.md").read_text()

        for phrase in ["Query Planner JSON", "Evidence Cards", "Reranker JSON", "Context Budget", "Citation Validation"]:
            self.assertIn(phrase, retrieval_doc)
        for phrase in ["Broad Retrieval", "lexical/entity sweep", "quote bank"]:
            self.assertIn(phrase, retrieval_doc)
        self.assertIn("SEAI_RETRIEVAL_FLOW.md", indexing_doc)
        self.assertIn("complete standalone claims", indexing_doc)


if __name__ == "__main__":
    unittest.main()
