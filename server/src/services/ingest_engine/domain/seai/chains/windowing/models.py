from dataclasses import dataclass, field
from typing import Optional
import uuid

@dataclass
class ChunkNode:
    text: str
    word_count: int
    start_idx: int
    end_idx: int
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prev: Optional['ChunkNode'] = None
    next: Optional['ChunkNode'] = None
    prev_context: Optional[dict] = None
    next_context: Optional[dict] = None
    
    # Hierarchy fields
    parent: Optional['ChunkNode'] = None
    children: list['ChunkNode'] = None
    
    # LLM Extracted Data
    summary: Optional[str] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []

    def to_dict(self):
        return {
            "text": self.text,
            "word_count": self.word_count,
            "start_idx": self.start_idx,
            "end_idx": self.end_idx,
            "prev_context": self.prev_context,
            "next_context": self.next_context
        }
