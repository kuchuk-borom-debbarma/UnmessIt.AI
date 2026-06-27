from abc import ABC, abstractmethod

class RetrievalServiceContract(ABC):
    """
    Inbound contract for the retrieval engine.
    """
    
    @abstractmethod
    def query(self, text: str) -> dict:
        """
        Executes a retrieval query to fetch relevant information and synthesizes an answer.
        :param text: The user's query text.
        :return: A dictionary containing 'answer' and 'citations'.
        """
        pass
