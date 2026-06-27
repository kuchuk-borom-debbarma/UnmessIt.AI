from abc import ABC, abstractmethod


class IngestRepository(ABC):
    @abstractmethod
    def save_raw_input(self, job_id: str, raw_content: str) -> str:
        """
        Saves just the raw input and returns the raw_input_id.
        """
        pass

    @abstractmethod
    def save_seai(self, episodes: list[dict], atoms: list[dict]) -> None:
        pass
