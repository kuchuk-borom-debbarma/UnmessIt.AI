from abc import ABC, abstractmethod


class Ingestor(ABC):

    @abstractmethod
    def ingest(self, data: str):
        """
        Clean up the data
        :param data: The data to preprocess
        :return: cleaned up data
        """
