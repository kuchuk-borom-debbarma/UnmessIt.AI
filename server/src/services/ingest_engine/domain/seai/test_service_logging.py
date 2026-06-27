import logging
import unittest

from src.infra.uuid_factory import UUIDFactory
from src.services.ingest_engine.domain.seai.chains.atom_code_verify_chain import AtomCodeVerifyChain
from src.services.ingest_engine.domain.seai.chains.source_window_chain import SourceWindowChain
from src.services.ingest_engine.domain.seai.chains.strict_fastcoref_chain import NoopPreprocessor
from src.services.ingest_engine.domain.seai.ingestor import SEAIChains, SEAIIngestor
from src.services.ingest_engine.domain.seai.models import SEAIConfig
from src.services.ingest_engine.domain.seai.utils.evidence import EvidenceResolver


class FakeRepo:
    def save_raw_input(self, job_id, raw_content):
        return "raw_1"

    def save_seai(self, episodes, atoms):
        self.episodes = episodes
        self.atoms = atoms


class FakeSplitter:
    def run(self, raw_text, prev_context="", next_context=""):
        return [{"summary": "private note", "evidence_quotes": [raw_text]}]


class FakeSummarizer:
    def run(self, episode_text, fallback=""):
        return fallback or "summary"


class FakeExtractor:
    def run(self, episode_text):
        return [{
            "content": "Private phrase was mentioned.",
            "evidence_quotes": ["PRIVATE_RAW_TEXT"],
            "atom_role": "direct",
            "annotations": [],
            "confidence": 0.9,
        }]


class FakeVerifier:
    def run(self, episode_text, atoms):
        return atoms


class FakeEpisodeVerifier:
    def run(self, episode_text, summary, fallback=""):
        return summary


class TestSEAIServiceLogging(unittest.TestCase):
    def test_lifecycle_logs_counts_and_data_previews(self):
        config = SEAIConfig()
        id_factory = UUIDFactory()
        ingestor = SEAIIngestor(
            config=config,
            repository=FakeRepo(),
            vector_indexer=None,
            chains=SEAIChains(
                preprocess=NoopPreprocessor(),
                window=SourceWindowChain(config),
                split_episodes=FakeSplitter(),
                summarize_episode=FakeSummarizer(),
                verify_episode=FakeEpisodeVerifier(),
                extract_atoms=FakeExtractor(),
                verify_atoms=FakeVerifier(),
                code_verify_atoms=AtomCodeVerifyChain(config, id_factory),
            ),
            id_factory=id_factory,
            evidence_resolver=EvidenceResolver(),
        )

        with self.assertLogs("src.services.ingest_engine.domain.seai", level=logging.INFO) as logs:
            ingestor.ingest("PRIVATE_RAW_TEXT", job_id="job_log")

        output = "\n".join(logs.output)
        self.assertIn("seai_ingest_start", output)
        self.assertIn("window_count=1", output)
        self.assertIn("episode_count=1", output)
        self.assertIn("atom_count=1", output)
        self.assertIn("PRIVATE_RAW_TEXT", output)
        self.assertIn("Private phrase was mentioned.", output)


if __name__ == "__main__":
    unittest.main()
