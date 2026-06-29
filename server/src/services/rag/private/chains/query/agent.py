from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from src.infra.langchain_json import _get_chat_llm
from src.repositories import directories, notes
from src.services.rag.private.chains.query import QueryEvidenceChain

logger = logging.getLogger(__name__)

class StopAgentException(Exception):
    """Raised by the submit_final_answer tool to break out of the agent loop.
    
    Why use an exception to stop the agent?
    1. We need to return a heavily structured dictionary to the UI (citations, dirs, notes).
    2. LangGraph's prebuilt create_react_agent serializes tool outputs into strings if we 
       let it finish naturally or if we use return_direct=True.
    3. Raising a control-flow exception short-circuits the LLM loop instantly and lets 
       us extract the exact Python dictionary without any parsing or serialization loss, 
       saving us from having to build a massive custom LangGraph state machine.
    """
    def __init__(self, data: dict[str, Any]):
        self.data = data


class QueryAgentChain:
    """Agentic entry point for queries. Replaces static pipeline."""

    def __init__(self, json_client) -> None:
        self.evidence_chain = QueryEvidenceChain(json_client)

    async def run(self, query: str, user_id: str, reporter=None) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
        """Run the agent loop and return (structured_answer, gathered_chunks, trace)."""
        gathered_chunks: dict[str, dict[str, Any]] = {}
        trace_parts: list[dict[str, Any]] = []

        @tool
        async def search_knowledge_base(search_query: str) -> str:
            """Search the knowledge base for semantic evidence. Returns summarized source chunks."""
            if reporter:
                await reporter.report(f"Searching knowledge base for: {search_query}")
            chunks, trace = await self.evidence_chain.run(search_query, user_id, reporter)
            trace_parts.append(trace)
            for c in chunks:
                gathered_chunks[c["id"]] = c
            if not chunks:
                return "No evidence found."
            return f"Found {len(chunks)} chunks:\n" + json.dumps(
                [{"id": c["id"], "summary": c.get("summary")} for c in chunks],
                indent=2
            )

        @tool
        def list_directories(parent_id: str | None = None) -> str:
            """List subdirectories. Pass None for root directories."""
            dirs = directories.list_children(user_id, parent_id)
            if not dirs:
                return "No directories found."
            return json.dumps([{"id": d["id"], "name": d["name"]} for d in dirs], indent=2)

        @tool
        def list_notes_in_directory(directory_id: str | None = None) -> str:
            """List all notes within a specific directory. Pass None for notes in the root."""
            all_notes = notes.list_notes(user_id, directory_id)
            if not all_notes:
                return "No notes found in this directory."
            return json.dumps(
                [{"id": n["id"], "snippet": str(n["text"])[:50] + "..."} for n in all_notes],
                indent=2
            )

        @tool
        def read_note(note_id: str) -> str:
            """Read the full text of a specific note."""
            note = notes.get(note_id, user_id)
            if note:
                return note["text"]
            return "Note not found."

        @tool
        def submit_final_answer(
            answer: str,
            citation_ids: list[str],
            directory_ids: list[str],
            note_ids: list[str]
        ) -> str:
            """Submit the final formulated answer to the user.
            
            Args:
                answer: The markdown-formatted response answering the user's query.
                citation_ids: List of source_chunk ids you are citing from search_knowledge_base.
                directory_ids: List of directory ids you are referencing.
                note_ids: List of note ids you are referencing.
            """
            # Raise our control-flow exception to instantly halt the LangGraph execution
            # and pass the structured dictionary directly back to the caller.
            raise StopAgentException({
                "answer": answer,
                "citations": citation_ids,
                "directories": directory_ids,
                "notes": note_ids
            })

        tools = [
            search_knowledge_base,
            list_directories,
            list_notes_in_directory,
            read_note,
            submit_final_answer
        ]

        system = """You are a helpful assistant with access to the user's notes, directories, and semantic knowledge base.
If the user asks a semantic or factual question, use `search_knowledge_base`.
If the user asks about their folders or notes structurally, use the directory and note tools.
You can use multiple tools to gather information before answering.
When you have enough information to answer the user's query, you MUST call the `submit_final_answer` tool.
Never output the final answer directly as a plain text message; ALWAYS use `submit_final_answer`.
"""

        llm = _get_chat_llm(user_id)
        agent = create_react_agent(llm, tools=tools, prompt=system)
        
        final_result = None
        try:
            await agent.ainvoke({"messages": [HumanMessage(content=query)]})
        except StopAgentException as e:
            final_result = e.data
        except Exception as exc:
            logger.error("Agent run failed: %s", exc)

        if not final_result:
            final_result = {
                "answer": "I could not generate an answer.",
                "citations": [],
                "directories": [],
                "notes": [],
            }

        trace = {
            "mode": "agentic",
            "query": query,
            "tool_traces": trace_parts
        }

        return final_result, list(gathered_chunks.values()), trace
