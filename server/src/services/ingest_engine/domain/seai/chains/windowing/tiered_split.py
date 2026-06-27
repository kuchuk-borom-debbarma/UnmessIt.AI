import re
from typing import List, Optional
from src.services.ingest_engine.domain.seai.chains.windowing.models import ChunkNode


class TieredSplitter:
    """
    Splits text into chunks using tiered fallback strategy.
    Returns a linked list of ChunkNodes.

    Input: raw text string
    Output: list of ChunkNode objects
    """

    def __init__(self, word_limit: int = 1500, char_limit: int = 6000):
        self.word_limit = word_limit
        self.char_limit = char_limit

    def chain(self, data: str) -> Optional[List[ChunkNode]]:
        """Chain method entry point."""
        return self._split(data)

    def _split(self, text: str) -> Optional[List[ChunkNode]]:
        """
        Split text and return list of ChunkNodes. Returns None if text is already within limits.
        """
        if not text.strip():
            return None

        original_text = text
        text = text.strip()

        # Fits in one chunk? Return None to indicate no splitting was necessary.
        if len(text.split()) <= self.word_limit and len(text) <= self.char_limit:
            return None

        # Try tier 1: split by paragraphs
        chunks = []
        for para in re.split(r"\n\s*\n", text):
            para = para.strip()
            if not para:
                continue

            if len(para.split()) <= self.word_limit and len(para) <= self.char_limit:
                start_idx = original_text.find(para)
                end_idx = start_idx + len(para)
                chunks.append(self._make_chunk(para, start_idx, end_idx))
            else:
                # Paragraph too big, try tier 2
                para_chunks = self._split_by_sentences(para, original_text)
                chunks.extend(para_chunks)

        self._link_chunks(chunks)
        return chunks

    def _split_by_sentences(self, text: str, original_text: str) -> List[ChunkNode]:
        """Tier 2: Split by sentence boundaries"""
        sentences = re.split(r"[.!?]\s+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        current = []
        current_words = 0

        for sent in sentences:
            sent_words = len(sent.split())

            # Sentence alone is too big, use tier 3
            if sent_words > self.word_limit or len(sent) > self.char_limit:
                if current:
                    chunk_text = " ".join(current)
                    start_idx = original_text.find(chunk_text)
                    end_idx = start_idx + len(chunk_text)
                    chunks.append(self._make_chunk(chunk_text, start_idx, end_idx))
                    current = []
                    current_words = 0
                chunks.extend(self._split_by_words(sent, original_text))
            # Adding sentence would exceed limit
            elif current_words + sent_words > self.word_limit:
                if current:
                    chunk_text = " ".join(current)
                    start_idx = original_text.find(chunk_text)
                    end_idx = start_idx + len(chunk_text)
                    chunks.append(self._make_chunk(chunk_text, start_idx, end_idx))
                current = [sent]
                current_words = sent_words
            # Add to current chunk
            else:
                current.append(sent)
                current_words += sent_words

        if current:
            chunk_text = " ".join(current)
            start_idx = original_text.find(chunk_text)
            end_idx = start_idx + len(chunk_text)
            chunks.append(self._make_chunk(chunk_text, start_idx, end_idx))

        return chunks

    def _split_by_words(self, text: str, original_text: str) -> List[ChunkNode]:
        """Tier 3: Split by word boundaries"""
        words = text.split()
        chunks = []
        current = []
        current_chars = 0

        for word in words:
            word_len = len(word) + 1  # +1 for space

            # Word alone exceeds limit
            if len(word) > self.char_limit:
                if current:
                    chunk_text = " ".join(current)
                    start_idx = original_text.find(chunk_text)
                    end_idx = start_idx + len(chunk_text)
                    chunks.append(self._make_chunk(chunk_text, start_idx, end_idx))
                    current = []
                    current_chars = 0
                start_idx = original_text.find(word)
                end_idx = start_idx + len(word)
                chunks.append(self._make_chunk(word, start_idx, end_idx))
                continue

            # Adding word would exceed limit
            if current_chars + word_len > self.char_limit:
                if len(current) > 1:
                    current.pop()  # Back up to 2nd-last word
                if current:
                    chunk_text = " ".join(current)
                    start_idx = original_text.find(chunk_text)
                    end_idx = start_idx + len(chunk_text)
                    chunks.append(self._make_chunk(chunk_text, start_idx, end_idx))
                current = [word]
                current_chars = word_len
            else:
                current.append(word)
                current_chars += word_len

        if current:
            chunk_text = " ".join(current)
            start_idx = original_text.find(chunk_text)
            end_idx = start_idx + len(chunk_text)
            chunks.append(self._make_chunk(chunk_text, start_idx, end_idx))

        return chunks

    @staticmethod
    def _make_chunk(text: str, start_idx: int, end_idx: int) -> ChunkNode:
        """Create a ChunkNode"""
        return ChunkNode(
            text=text,
            word_count=len(text.split()),
            start_idx=start_idx,
            end_idx=end_idx
        )

    @staticmethod
    def _link_chunks(chunks: List[ChunkNode]):
        """Links the chunks together using prev and next pointers."""
        for i in range(len(chunks)):
            if i > 0:
                chunks[i].prev = chunks[i - 1]
            if i < len(chunks) - 1:
                chunks[i].next = chunks[i + 1]
