import chromadb
import logging
from chromadb.utils import embedding_functions
from kink import inject
from typing import List, Dict, Any

from src.infra.settings import Settings
from src.infra.sqlite import BASE_DIR
from src.infra.rate_limit import PerMinuteRateLimiter, RateLimitedEmbeddingFunction
from src.services.retrieval_engine.ports.outbound.VectorStoreContract import VectorStoreContract

logger = logging.getLogger(__name__)

@inject
class ChromaVectorStoreImpl(VectorStoreContract):
    def __init__(self, settings: Settings):
        self.settings = settings
        
        # Initialize embedding function based on settings
        if settings.embedding_provider.lower() == "ollama":
            self.embedding_function = embedding_functions.OllamaEmbeddingFunction(
                url=settings.embedding_base_url or "http://localhost:11434/api/embeddings",
                model_name=settings.embedding_model
            )
        elif settings.embedding_provider.lower() == "openai":
            self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_key=settings.embedding_api_key,
                api_base=settings.embedding_base_url or "https://api.openai.com/v1",
                model_name=settings.embedding_model
            )
        else:
            raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")

        if settings.embedding_rate_limit_per_minute > 0:
            self.embedding_function = RateLimitedEmbeddingFunction(
                self.embedding_function,
                PerMinuteRateLimiter(settings.embedding_rate_limit_per_minute),
            )

        # Initialize ChromaDB client (persistent)
        # Store in the server/data directory to sit alongside SQLite
        db_path = str(BASE_DIR / "data" / "chroma_db")
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Get or create collection
        self.collection = None
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        try:
            self.collection = self.client.get_or_create_collection(
                name="statements",
                embedding_function=self.embedding_function
            )
        except ValueError as exc:
            if "embedding function" not in str(exc).lower():
                raise
            # ponytail: embedding provider changed; old vectors are incompatible, so reset collection.
            self.client.delete_collection("statements")
            self.collection = self.client.create_collection(
                name="statements",
                embedding_function=self.embedding_function
            )

    def add_statements(self, statement_ids: List[str], texts: List[str], metadatas: List[Dict[str, Any]]) -> None:
        """Embeds and stores statements in ChromaDB"""
        if not statement_ids:
            return
            
        # ponytail: we overwrite existing statements if they share the same ID. 
        # For upsert behavior, `add` might fail if IDs exist, so we use `upsert`.
        try:
            self.collection.upsert(
                ids=statement_ids,
                documents=texts,
                metadatas=metadatas
            )
        except Exception as exc:
            if "does not exist" not in str(exc).lower():
                raise
            logger.warning("chroma_collection_missing_recreate")
            self._ensure_collection()
            self.collection.upsert(
                ids=statement_ids,
                documents=texts,
                metadatas=metadatas
            )

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Searches the vector store for statements similar to the query."""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )
        except Exception as exc:
            if "does not exist" not in str(exc).lower():
                raise
            logger.warning("chroma_collection_missing_recreate")
            self._ensure_collection()
            return []
        
        parsed_results = []
        if not results['ids'] or not results['ids'][0]:
            return parsed_results

        for idx, statement_id in enumerate(results['ids'][0]):
            metadata = results['metadatas'][0][idx] if results['metadatas'] else {}
            object_id = metadata.get("object_id") or metadata.get("chunk_id", statement_id)
            parsed_results.append({
                "statement_id": object_id,
                "object_id": object_id,
                "object_type": metadata.get("object_type", "legacy_chunk"),
                "vector_id": statement_id,
                "kind": metadata.get("kind", "text"),
                "text": results['documents'][0][idx],
                "metadata": metadata,
                "distance": results['distances'][0][idx] if results['distances'] else 0.0
            })
            
        return parsed_results

    def reset(self) -> None:
        """Wipes the entire Chroma vector store collection."""
        try:
            self.client.delete_collection("statements")
        except Exception as e:
            pass # ignore if doesn't exist
        self.collection = self.client.get_or_create_collection(
            name="statements",
            embedding_function=self.embedding_function
        )
