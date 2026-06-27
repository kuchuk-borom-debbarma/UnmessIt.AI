from typing import List, Dict, Any
from abc import ABC, abstractmethod

class RetrievalRepositoryContract(ABC):
    """
    Contract for retrieving relational data (like statements and nodes) for the retrieval engine.
    """
    
    @abstractmethod
    def get_statements_by_ids(self, statement_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Retrieves full statement details (including text and source IDs) by their IDs.
        :param statement_ids: List of statement IDs.
        :return: List of dictionaries with statement details.
        """
        pass

    def get_children_by_parent_ids(self, parent_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Retrieves child chunks for parent chunk IDs.
        """
        pass

    def get_episodes_by_ids(self, episode_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Retrieves SEAI episodes by IDs.
        """
        pass

    def get_atoms_by_ids(self, atom_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Retrieves SEAI atoms by IDs.
        """
        pass

    def get_atoms_by_episode_ids(self, episode_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Retrieves SEAI atoms for episode IDs.
        """
        pass

    def search_episodes_by_terms(self, terms: List[str], limit: int = 12) -> List[Dict[str, Any]]:
        """
        Retrieves SEAI episodes by simple lexical term match.
        """
        pass

    def search_atoms_by_terms(self, terms: List[str], limit: int = 16) -> List[Dict[str, Any]]:
        """
        Retrieves SEAI atoms by simple lexical term match.
        """
        pass
