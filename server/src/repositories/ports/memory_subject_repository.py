from abc import ABC, abstractmethod
from typing import Any


class MemorySubjectRepository(ABC):
    @abstractmethod
    def find_candidate_subjects(self, terms: list[str], limit: int = 12) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def save_subject_index(self, subjects: list[dict[str, Any]], links: list[dict[str, Any]]) -> None:
        pass

    @abstractmethod
    def get_subject_links(self, subject_ids: list[str], limit: int = 24) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def wipe_subjects(self) -> None:
        pass
