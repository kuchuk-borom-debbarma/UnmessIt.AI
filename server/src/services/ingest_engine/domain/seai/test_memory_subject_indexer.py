import unittest

from src.services.ingest_engine.domain.seai.memory_subject_indexer import MemorySubjectIndexer


EPISODE = {
    "id": "episode_1",
    "raw_input_id": "raw_1",
    "summary": "UnmessIt needs broader recall.",
    "text": "UnmessIt needs broader recall.",
}
ATOM = {
    "id": "atom_1",
    "raw_input_id": "raw_1",
    "episode_id": "episode_1",
    "content": "UnmessIt needs broader recall.",
}


class FakeRepo:
    def __init__(self, candidates=None):
        self.candidates = candidates or []
        self.saved_subjects = []
        self.saved_links = []

    def find_candidate_subjects(self, terms, limit=12):
        self.terms = terms
        return self.candidates

    def save_subject_index(self, subjects, links):
        self.saved_subjects = subjects
        self.saved_links = links


class FakeChain:
    def __init__(self, data):
        self.data = data

    def run(self, raw_preview, episodes, atoms, candidate_subjects):
        self.call = (raw_preview, episodes, atoms, candidate_subjects)
        return self.data


class FakeIdFactory:
    def __init__(self):
        self.next_id = 0

    def new_id(self):
        self.next_id += 1
        return f"id_{self.next_id}"


class TestMemorySubjectIndexer(unittest.TestCase):
    def test_creates_subject_and_link(self):
        repo = FakeRepo()
        chain = FakeChain({
            "subjects": [{
                "ref": "s1",
                "name": "UnmessIt recall",
                "kind": "topic",
                "aliases": ["broad recall"],
                "summary": "Recall across accumulated notes.",
            }],
            "links": [{
                "subject_ref": "s1",
                "episode_id": "episode_1",
                "atom_id": "atom_1",
                "relation": "problem",
                "confidence": 0.9,
                "reason": "The atom names the recall problem.",
                "time_label": "current",
            }],
        })

        result = MemorySubjectIndexer(repo, chain, FakeIdFactory()).index("UnmessIt needs broader recall.", [EPISODE], [ATOM])

        self.assertEqual(result["subjects"], 1)
        self.assertEqual(result["links"], 1)
        self.assertEqual(result["draft_subjects"], 1)
        self.assertEqual(result["draft_links"], 1)
        self.assertEqual(result["rejected_links"], 0)
        self.assertEqual(repo.saved_subjects[0]["name"], "UnmessIt recall")
        self.assertEqual(repo.saved_links[0]["atom_id"], "atom_1")

    def test_reuses_existing_subject(self):
        existing = {
            "id": "subject_existing",
            "name": "UnmessIt",
            "kind": "project",
            "aliases": ["UnmessIt.AI"],
            "summary": "Source-backed memory app.",
        }
        repo = FakeRepo(candidates=[existing])
        chain = FakeChain({
            "subjects": [{
                "ref": "s1",
                "existing_subject_id": "subject_existing",
                "name": "UnmessIt",
                "kind": "project",
                "aliases": ["recall work"],
                "summary": "Source-backed memory app with recall work.",
            }],
            "links": [{"subject_ref": "s1", "episode_id": "episode_1", "relation": "status"}],
        })

        MemorySubjectIndexer(repo, chain, FakeIdFactory()).index("UnmessIt needs broader recall.", [EPISODE], [ATOM])

        self.assertEqual(repo.saved_subjects[0]["id"], "subject_existing")
        self.assertIn("UnmessIt.AI", repo.saved_subjects[0]["aliases"])

    def test_ignores_invalid_evidence_links(self):
        repo = FakeRepo()
        chain = FakeChain({
            "subjects": [{"ref": "s1", "name": "UnmessIt", "kind": "project"}],
            "links": [
                {"subject_ref": "s1", "episode_id": "missing", "relation": "mentions"},
                {"subject_ref": "s1", "episode_id": "episode_1", "atom_id": "missing", "relation": "mentions"},
            ],
        })

        result = MemorySubjectIndexer(repo, chain, FakeIdFactory()).index("UnmessIt needs broader recall.", [EPISODE], [ATOM])

        self.assertEqual(result["subjects"], 0)
        self.assertEqual(result["links"], 0)
        self.assertEqual(result["draft_subjects"], 1)
        self.assertEqual(result["draft_links"], 2)
        self.assertEqual(result["rejected_links"], 2)
        self.assertEqual(result["rejected_subjects"], 1)
        self.assertEqual(repo.saved_subjects, [])
        self.assertEqual(repo.saved_links, [])


if __name__ == "__main__":
    unittest.main()
