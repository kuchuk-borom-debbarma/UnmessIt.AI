from typing import List
from src.services.ingest_engine.domain.seai.chains.windowing.models import ChunkNode


class ContextAdder:
    """
    Adds prev/next overlap context to ChunkNodes.
    Uses the linked list pointers (prev, next) on the ChunkNode.

    Input: list of ChunkNodes
    Output: list of ChunkNodes with prev_context and next_context populated
    """

    def __init__(self, overlap_size: int = 200):
        self.overlap_size = overlap_size

    def chain(self, chunks: List[ChunkNode]) -> List[ChunkNode]:
        """Chain method entry point."""
        return self._add_overlap(chunks)

    def _add_overlap(self, chunks: List[ChunkNode]) -> List[ChunkNode]:
        """
        Add prev/next context to each chunk using their linked nodes.
        prev_context = last overlap_size chars of previous chunk text
        next_context = first overlap_size chars of next chunk text
        Returns dicts containing the text and their exact start/end positions.
        """
        if not chunks:
            return []

        for chunk in chunks:
            # Add previous context
            if chunk.prev:
                prev_text = chunk.prev.text
                if prev_text:
                    overlap_text = prev_text[-self.overlap_size:]
                    start_pos = chunk.prev.end_idx - len(overlap_text)
                    chunk.prev_context = {
                        "text": overlap_text,
                        "start_idx": start_pos,
                        "end_idx": chunk.prev.end_idx
                    }

            # Add next context
            if chunk.next:
                next_text = chunk.next.text
                if next_text:
                    overlap_text = next_text[:self.overlap_size]
                    end_pos = chunk.next.start_idx + len(overlap_text)
                    chunk.next_context = {
                        "text": overlap_text,
                        "start_idx": chunk.next.start_idx,
                        "end_idx": end_pos
                    }

        return chunks
