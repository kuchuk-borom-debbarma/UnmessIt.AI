from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from ._breakdown import breakdown_node
from ._search import search_node
from ._state import QueryState
from ._subjects import subjects_node


def build_retrieval_graph(json_client) -> Any:
    """Build and compile the retrieval StateGraph.

    Graph shape:
        START → breakdown → subjects → search → END

    breakdown: decomposes the user query into focused sub-queries (LLM).
    subjects:  extracts subjects the query implies by description (LLM).
               results feed directly into recall key lookup in search.
    search:    runs vector + lexical + recall evidence search per sub-query.

    The graph is compiled once at QueryEvidenceChain construction and reused
    for every call, so the StateGraph compilation cost is paid only once.
    """
    graph = StateGraph(QueryState)

    graph.add_node("breakdown", breakdown_node(json_client))
    graph.add_node("subjects", subjects_node(json_client))
    graph.add_node("search", search_node)

    graph.add_edge(START, "breakdown")
    graph.add_edge("breakdown", "subjects")
    graph.add_edge("subjects", "search")
    graph.add_edge("search", END)

    return graph.compile()
