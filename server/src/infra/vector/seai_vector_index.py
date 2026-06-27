from __future__ import annotations

import json
import logging

from src.services.ingest_engine.domain.seai.models import Atom, Episode

logger = logging.getLogger(__name__)


class ChromaSEAIVectorIndex:
    def __init__(self, vector_store):
        self.vector_store = vector_store

    def add(self, episodes: list[Episode], atoms: list[Atom]) -> None:
        if not self.vector_store:
            return

        ids, texts, metadatas = [], [], []
        for episode in episodes:
            ids.append(f"{episode['id']}:episode")
            texts.append(f"{episode['summary']}\n{episode['text']}")
            metadatas.append({
                "object_type": "episode",
                "object_id": episode["id"],
                "episode_id": episode["id"],
                "raw_input_id": episode["raw_input_id"],
                "kind": "episode",
                "spans": json.dumps(episode["spans"], ensure_ascii=False),
            })

        for atom in atoms:
            ids.append(f"{atom['id']}:atom")
            texts.append(atom["content"])
            metadatas.append({
                "object_type": "atom",
                "object_id": atom["id"],
                "atom_id": atom["id"],
                "episode_id": atom["episode_id"],
                "raw_input_id": atom["raw_input_id"],
                "atom_role": atom["atom_role"],
                "confidence": atom["confidence"],
                "kind": "atom",
                "evidence_spans": json.dumps(atom["evidence_spans"], ensure_ascii=False),
            })

        logger.info("seai_vector_index_start document_count=%s episode_count=%s atom_count=%s", len(ids), len(episodes), len(atoms))
        self.vector_store.add_statements(ids, texts, metadatas)
        logger.info("seai_vector_index_complete document_count=%s", len(ids))
