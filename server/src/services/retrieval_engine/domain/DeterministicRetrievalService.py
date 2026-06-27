from __future__ import annotations

from typing import Any

from kink import inject

from src.services.retrieval_engine.domain.seai.answer_generator import StrictAnswerGenerator
from src.services.retrieval_engine.domain.seai.cards import EvidenceCardBuilder, important_terms, unique
from src.services.retrieval_engine.domain.seai.citations import validated_legacy_response, validated_seai_response
from src.services.retrieval_engine.domain.seai.context import (
    broaden_context_cards,
    is_broad_query,
    objects_from_cards,
    pack_evidence_context,
    pack_legacy_context,
)
from src.services.retrieval_engine.domain.seai.json_utils import (
    normalize_plan_json as _normalize_plan_json,
    normalize_query as _normalize_query,
)
from src.services.retrieval_engine.domain.seai.models import (
    Citation,
    CitedAnswer,
    RerankDecision,
    RetrievalPlan,
)
from src.services.retrieval_engine.domain.seai.planner import QueryPlanner
from src.services.retrieval_engine.domain.seai.reranker import EvidenceReranker
from src.services.retrieval_engine.ports.inbound.RetrievalServiceContract import RetrievalServiceContract
from src.services.retrieval_engine.ports.outbound.RetrievalRepositoryContract import RetrievalRepositoryContract
from src.services.retrieval_engine.ports.outbound.VectorStoreContract import VectorStoreContract


@inject
class DeterministicRetrievalService(RetrievalServiceContract):
    def __init__(
        self,
        vector_store: VectorStoreContract,
        retrieval_repo: RetrievalRepositoryContract,
        memory_subject_repo=None,
        query_planner=None,
        evidence_reranker=None,
        answer_generator=None,
    ):
        self.vector_store = vector_store
        self.retrieval_repo = retrieval_repo
        self.memory_subject_repo = memory_subject_repo
        self.query_planner = query_planner
        self.evidence_reranker = evidence_reranker
        self.answer_generator = answer_generator
        self.card_builder = EvidenceCardBuilder(retrieval_repo)

    def query(self, text: str) -> dict:
        normalized_text = _normalize_query(text)
        vector_hits = self.vector_store.search(normalized_text, top_k=16)
        seai_hits = [
            hit for hit in vector_hits
            if hit.get("metadata", {}).get("object_type") in {"atom", "episode"}
        ]
        if seai_hits or (is_broad_query(normalized_text) and self.memory_subject_repo):
            return self._query_seai(normalized_text, seai_hits)
        return self._query_legacy_chunks(normalized_text, vector_hits)

    def _query_seai(self, text: str, vector_hits: list[dict[str, Any]]) -> dict:
        plan = self.query_planner.plan(text)
        pending_queries = unique([text, *plan.search_queries])
        cards_by_id: dict[str, dict[str, Any]] = {}
        selected_ids: list[str] = []
        broad_query = is_broad_query(text)
        trace = {
            "plan": plan.model_dump(),
            "normalized_query": text,
            "broad_query": broad_query,
            "rounds": [],
            "selected_evidence_ids": [],
            "quote_bank_ids": [],
            "lexical_sweep_count": 0,
            "resolved_subject_ids": [],
            "subject_evidence_count": 0,
            "subject_card_count": 0,
            "context_char_count": 0,
            "answer_retry": False,
        }

        if broad_query and self.memory_subject_repo:
            terms = important_terms([
                text,
                *plan.search_queries,
                *plan.must_find,
                *plan.constraints,
            ])
            subjects = self.memory_subject_repo.find_candidate_subjects(terms, limit=5)
            trace["resolved_subject_ids"] = [subject["id"] for subject in subjects]
            subject_links = self.memory_subject_repo.get_subject_links(trace["resolved_subject_ids"], limit=24)
            trace["subject_evidence_count"] = len(subject_links)
            for card in self.card_builder.from_subject_links(subject_links):
                cards_by_id.setdefault(card["evidence_id"], card)
            trace["subject_card_count"] = len(cards_by_id)

        for round_no in range(1, 4):
            round_hits = vector_hits if round_no == 1 else []
            for search_query in pending_queries:
                round_hits.extend(self.vector_store.search(search_query, top_k=12))

            for card in self.card_builder.from_hits(round_hits):
                cards_by_id[card["evidence_id"]] = card
            if broad_query:
                lexical_cards = self.card_builder.lexical_sweep(text, plan)
                trace["lexical_sweep_count"] = max(trace["lexical_sweep_count"], len(lexical_cards))
                for card in lexical_cards:
                    cards_by_id.setdefault(card["evidence_id"], card)

            cards = sorted(
                cards_by_id.values(),
                key=lambda card: (card.get("distance") is None, card.get("distance") or 0.0)
            )
            decision = self.evidence_reranker.rerank(text, plan, cards, round_no)
            valid_selected = [eid for eid in decision.selected_evidence_ids if eid in cards_by_id]
            for evidence_id in valid_selected:
                if evidence_id not in selected_ids:
                    selected_ids.append(evidence_id)

            trace["rounds"].append({
                "round": round_no,
                "queries": pending_queries,
                "candidate_count": len(cards),
                "selected_evidence_ids": valid_selected,
                "scores": [score.model_dump() for score in decision.scores],
                "missing_aspects": decision.missing_aspects,
                "follow_up_queries": decision.follow_up_queries,
                "enough_evidence": decision.enough_evidence,
            })

            next_queries = [query for query in decision.follow_up_queries if query not in pending_queries]
            if decision.enough_evidence and not decision.missing_aspects:
                break
            if not next_queries:
                break
            pending_queries = next_queries

        if not selected_ids:
            selected_ids = [card["evidence_id"] for card in list(cards_by_id.values())[:6]]

        selected_cards = [cards_by_id[eid] for eid in selected_ids if eid in cards_by_id]
        selected_cards = broaden_context_cards(text, selected_cards, list(cards_by_id.values()), trace)
        if not selected_cards:
            return {"answer": "No sourced answer found.", "citations": [], "retrieval_trace": trace}

        context = pack_evidence_context(selected_cards)
        trace["selected_evidence_ids"] = [card["evidence_id"] for card in selected_cards]
        trace["quote_bank_ids"] = [card["object_id"] for card in selected_cards]
        trace["context_char_count"] = len(context)
        episodes, atoms = objects_from_cards(selected_cards)

        response = self._generate_and_validate_seai_answer(text, context, episodes, atoms)
        if response["answer"] == "No sourced answer found.":
            trace["answer_retry"] = True
            retry_context = pack_evidence_context(selected_cards, strict=True)
            trace["context_char_count"] = len(retry_context)
            response = self._generate_and_validate_seai_answer(text, retry_context, episodes, atoms)

        response["retrieval_trace"] = trace
        return response

    def _generate_and_validate_seai_answer(
        self,
        text: str,
        context: str,
        episodes: list[dict[str, Any]],
        atoms: list[dict[str, Any]],
    ) -> dict:
        self.answer_generator.init()
        try:
            answer = self.answer_generator.generate(text, context)
        finally:
            self.answer_generator.close()
        return validated_seai_response(answer, episodes, atoms)

    def _query_legacy_chunks(self, text: str, vector_hits: list[dict[str, Any]]) -> dict:
        chunk_ids = unique([hit["statement_id"] for hit in vector_hits])
        if not chunk_ids:
            return {"answer": "No sourced answer found.", "citations": []}

        chunks = self.retrieval_repo.get_statements_by_ids(chunk_ids)
        parents = self.retrieval_repo.get_statements_by_ids(
            unique([chunk["parent_id"] for chunk in chunks if chunk.get("parent_id")])
        )
        children = self.retrieval_repo.get_children_by_parent_ids(
            unique([chunk["id"] for chunk in chunks if (chunk.get("level") or 0) == 0])
        )

        context_chunks = _dedupe_chunks([*chunks, *parents, *children])
        if not context_chunks:
            return {"answer": "No sourced answer found.", "citations": []}

        context = pack_legacy_context(context_chunks)
        self.answer_generator.init()
        try:
            answer = self.answer_generator.generate(text, context)
        finally:
            self.answer_generator.close()

        return validated_legacy_response(answer, context_chunks)


def _dedupe_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    result = []
    for chunk in chunks:
        chunk_id = chunk.get("id")
        if chunk_id and chunk_id not in seen:
            seen.add(chunk_id)
            result.append(chunk)
    return result


__all__ = [
    "Citation",
    "CitedAnswer",
    "DeterministicRetrievalService",
    "RerankDecision",
    "RetrievalPlan",
    "_normalize_plan_json",
    "_normalize_query",
]
