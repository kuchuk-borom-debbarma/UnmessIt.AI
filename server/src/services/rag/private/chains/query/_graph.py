from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from ._breakdown import breakdown_node
from ._search import search_node
from ._state import QueryState


def build_retrieval_graph(json_client) -> Any:
    """Build and compile the retrieval StateGraph.

    Graph shape:
        START → breakdown → search → END

    breakdown: decomposes the user query into sub-queries (LLM).
    search: runs vector + lexical + recall evidence search for every sub-query.

    The graph is compiled once at QueryEvidenceChain construction and reused
    for every call, so the StateGraph compilation cost is paid only once.
    """
    graph = StateGraph(QueryState)

    graph.add_node("breakdown", breakdown_node(json_client))
    graph.add_node("search", search_node)

    graph.add_edge(START, "breakdown")
    graph.add_edge("breakdown", "search")
    graph.add_edge("search", END)

    return graph.compile()
