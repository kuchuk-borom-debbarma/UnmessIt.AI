from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict
from src.services.rag.models import ProgressReporter


class QueryState(TypedDict):
    """LangGraph state passed through the retrieval graph.

    sub_queries is Annotated with operator.add so each search node appends
    its found chunks without overwriting results from other sub-queries.
    chunks and trace_parts accumulate across sub-query passes.
    """

    query: str
    sub_queries: list[str]
    extracted_subjects: list[str]
    user_id: str
    reporter: ProgressReporter | None
    # operator.add merges chunk lists across parallel/sequential sub-query nodes.
    chunks: Annotated[list[dict[str, Any]], operator.add]
    trace_parts: Annotated[list[dict[str, Any]], operator.add]
