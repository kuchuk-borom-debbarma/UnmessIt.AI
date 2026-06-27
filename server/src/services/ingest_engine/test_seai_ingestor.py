import unittest

from src.infra.langchain.json_llm import LLMJsonClient
from src.infra.uuid_factory import UUIDFactory
from src.infra.vector.seai_vector_index import ChromaSEAIVectorIndex
from src.services.ingest_engine.domain.seai.chains.atom_code_verify_chain import AtomCodeVerifyChain
from src.services.ingest_engine.domain.seai.chains.episode_verify_chain import LLMEpisodeVerifier
from src.services.ingest_engine.domain.seai.chains.source_window_chain import SourceWindowChain
from src.services.ingest_engine.domain.seai.chains.strict_fastcoref_chain import NoopPreprocessor
from src.services.ingest_engine.domain.seai.ingestor import SEAIChains, SEAIIngestor
from src.services.ingest_engine.domain.seai.models import SEAIConfig
from src.services.ingest_engine.domain.seai.utils.evidence import EvidenceResolver


class FakeRepo:
    def __init__(self):
        self.events = []

    def save_raw_input(self, job_id, raw_content):
        self.events.append(("raw", job_id, raw_content))
        return "raw_1"

    def save_seai(self, episodes, atoms):
        self.events.append(("seai", len(episodes), len(atoms)))


class FakeVectorStore:
    def __init__(self):
        self.calls = []

    def add_statements(self, ids, texts, metadatas):
        self.calls.append((ids, texts, metadatas))


class FakeSplitter:
    def run(self, raw_text, prev_context="", next_context=""):
        return [{"summary": "Amy memory.", "evidence_quotes": ["Amy likes coffee.", "Amy bought beans."]}]


class FakeSummarizer:
    def run(self, episode_text, fallback=""):
        return fallback or "summary"


class FakeVerifier:
    def run(self, episode_text, atoms):
        return atoms


class FakeEpisodeVerifier:
    def run(self, episode_text, summary, fallback=""):
        return summary


class FakeExtractor:
    def run(self, episode_text):
        return [{
            "content": "Amy likes coffee.",
            "evidence_quotes": ["Amy likes coffee"],
            "atom_role": "direct",
            "annotations": ["preference"],
            "confidence": 0.9,
        }]


def make_ingestor(**overrides):
    config = SEAIConfig()
    id_factory = UUIDFactory()
    chains = SEAIChains(
        preprocess=NoopPreprocessor(),
        window=SourceWindowChain(config),
        split_episodes=overrides.get("splitter", FakeSplitter()),
        summarize_episode=overrides.get("summarizer", FakeSummarizer()),
        verify_episode=overrides.get("episode_verifier", FakeEpisodeVerifier()),
        extract_atoms=overrides.get("extractor", FakeExtractor()),
        verify_atoms=overrides.get("verifier", FakeVerifier()),
        code_verify_atoms=AtomCodeVerifyChain(config, id_factory),
    )
    return SEAIIngestor(
        config=config,
        repository=overrides.get("repo", FakeRepo()),
        vector_indexer=ChromaSEAIVectorIndex(overrides.get("vector_store", FakeVectorStore())),
        chains=chains,
        id_factory=id_factory,
        evidence_resolver=EvidenceResolver(),
    )


class TestSEAIIngestor(unittest.TestCase):
    def test_json_client_repairs_invalid_json(self):
        class RepairLLM:
            def __init__(self):
                self.calls = 0

            def invoke(self, messages):
                self.calls += 1
                content = '{"episodes":[{"summary":"one" "evidence_quotes":["Amy"]}]}' if self.calls == 1 else '{"episodes":[{"summary":"one","evidence_quotes":["Amy"]}]}'
                return type("Response", (), {"content": content})()

        data = LLMJsonClient(llm=RepairLLM(), max_retries=1).invoke_json("system", "human")

        self.assertEqual(data["episodes"][0]["summary"], "one")

    def test_episode_verifier_rewrites_bad_summary(self):
        class VerifyClient:
            def invoke_json(self, system, human):
                return {"summary": "Grisha gave Eren Titan powers."}

        summary = LLMEpisodeVerifier(VerifyClient()).verify_summary(
            "After the fall of Shiganshina, Grisha gave Eren Titan powers.",
            "Reiner Braun sacrificed himself.",
            "",
        )

        self.assertEqual(summary, "Grisha gave Eren Titan powers.")

    def test_ingest_saves_multispan_episode_and_atom(self):
        repo = FakeRepo()
        vector_store = FakeVectorStore()
        result = make_ingestor(repo=repo, vector_store=vector_store).ingest(
            "Amy likes coffee. Docker uses namespaces. Amy bought beans.",
            job_id="job_1",
        )

        self.assertEqual(repo.events[0][0], "raw")
        self.assertEqual(repo.events[1], ("seai", 1, 1))
        self.assertEqual(len(result["episodes"][0]["spans"]), 2)
        self.assertEqual(result["episodes"][0]["text"], "Amy likes coffee.\n...\nAmy bought beans.")
        self.assertEqual(result["atoms"][0]["content"], "Amy likes coffee.")
        self.assertEqual(vector_store.calls[0][2][0]["object_type"], "episode")

    def test_chain_failure_keeps_episode_without_killing_job(self):
        class FailingExtractor:
            def run(self, episode_text):
                raise RuntimeError("compute error")

        result = make_ingestor(extractor=FailingExtractor()).ingest("Amy likes coffee. Amy bought beans.", job_id="job_2")

        self.assertEqual(len(result["episodes"]), 1)
        self.assertEqual(result["atoms"], [])

    def test_large_inputs_are_windowed_with_overlap_context(self):
        class EchoSplitter:
            def __init__(self):
                self.calls = []

            def run(self, raw_text, prev_context="", next_context=""):
                self.calls.append((raw_text, prev_context, next_context))
                return [{"summary": "window", "evidence_quotes": [raw_text]}]

        splitter = EchoSplitter()
        ingestor = make_ingestor(splitter=splitter)
        ingestor.config.episode_chunk_word_limit = 5
        ingestor.config.episode_chunk_char_limit = 40
        ingestor.config.episode_overlap_chars = 10
        ingestor.ingest("alpha beta gamma delta epsilon.\n\nzeta eta theta iota kappa.\n\nlambda mu nu xi omicron.", job_id="job_3")

        self.assertGreater(len(splitter.calls), 1)
        self.assertTrue(any(prev or nxt for _, prev, nxt in splitter.calls))


if __name__ == "__main__":
    unittest.main()
