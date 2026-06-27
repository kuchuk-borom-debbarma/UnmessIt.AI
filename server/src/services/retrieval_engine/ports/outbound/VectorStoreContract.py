from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

class VectorStoreContract(ABC):
    """
    Contract for vector database interactions.
    Provides methods to add embedded statements and search them via similarity.
    """
    
    @abstractmethod
    def add_statements(self, statement_ids: List[str], texts: List[str], metadatas: List[Dict[str, Any]]) -> None:
        """
        Embeds and stores statements in the vector database.
        :param statement_ids: The unique IDs of the statements (used as document IDs).
        :param texts: The raw text of the statements.
        :param metadatas: Metadata dictionaries (e.g. {"paths": ["/alpha", "/beta"]}) for filtering.
        """
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Searches the vector store for statements similar to the query.
        :param query: The search query string.
        :param top_k: Number of results to return.
        :return: A list of dictionaries containing 'statement_id', 'text', 'metadata', and 'distance'.
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """
        Wipes the entire vector store collection.
        """
        pass
