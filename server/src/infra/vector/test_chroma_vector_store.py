import unittest

from src.infra.vector.chroma_vector_store import ChromaVectorStoreImpl


class MissingCollection:
    def __init__(self):
        self.calls = 0

    def upsert(self, **kwargs):
        self.calls += 1
        raise Exception("Collection [abc] does not exist.")


class WorkingCollection:
    def __init__(self):
        self.upserts = []

    def upsert(self, **kwargs):
        self.upserts.append(kwargs)


class FakeClient:
    def __init__(self):
        self.collection = WorkingCollection()

    def get_or_create_collection(self, name, embedding_function):
        return self.collection


class TestChromaVectorStoreImpl(unittest.TestCase):
    def test_add_recreates_missing_collection(self):
        store = ChromaVectorStoreImpl.__new__(ChromaVectorStoreImpl)
        store.embedding_function = object()
        store.client = FakeClient()
        store.collection = MissingCollection()

        store.add_statements(["id"], ["text"], [{"kind": "atom"}])

        self.assertEqual(len(store.client.collection.upserts), 1)


if __name__ == "__main__":
    unittest.main()
