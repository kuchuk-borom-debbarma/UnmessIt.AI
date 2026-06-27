import unittest

from src.services.ingest_engine.domain.seai.chains.subject_index_chain import SubjectIndexChain


class CaptureClient:
    def invoke_json(self, system, human):
        self.system = system
        self.human = human
        return {"subjects": [], "links": []}


class TestSubjectIndexChain(unittest.TestCase):
    def test_prompt_uses_compact_payloads(self):
        client = CaptureClient()
        chain = SubjectIndexChain(client)

        chain.run(
            "raw " * 1000,
            [{"id": "episode_1", "summary": "short summary", "text": "x" * 2000}],
            [{"id": "atom_1", "episode_id": "episode_1", "content": "y" * 1000, "annotations": ["a", "b", "c", "d", "e"]}],
            [{"id": "subject_1", "name": "Subject", "kind": "topic", "aliases": ["a"] * 10, "summary": "z" * 1000}],
        )

        self.assertNotIn("raw raw raw", client.human)
        self.assertNotIn("x" * 500, client.human)
        self.assertNotIn("y" * 500, client.human)
        self.assertNotIn("z" * 500, client.human)
        self.assertIn("at most 6 subjects and 18 links", client.human)


if __name__ == "__main__":
    unittest.main()
