# Query Breakdown Step + Rate Limiter Singleton Fix

**Branch:** `enhancement/query-breakdown-step` → `staging`

---

## What This Does

Complex multi-hop queries (e.g. *"where did the original lead of the project that Initech was absorbed into live when the company that spun out of it was formed?"*) would previously fail because retrieval fired a single vector search with the full raw query text. The most semantically noisy keywords dominated the results, crowding out the chunks that actually held the answer.

This PR adds a **query breakdown step** as the first node of a LangGraph retrieval graph, and fixes a **rate limiter bug** that gave every concurrent request its own independent token bucket.

---

## Changes

### 1. Rate Limiter Singleton (`infra/`)

**Bug:** `PerMinuteRateLimiter` was constructed fresh on every call to `_get_chat_llm()` and `_embedding_function()`. Each concurrent ingest job and retrieval call had its own independent counter, so the configured RPM cap was effectively multiplied by the number of concurrent callers.

**Fix:** Added `get_limiter(rpm)` — an `lru_cache`-backed factory returning one shared limiter per RPM value. Also cached `_get_chat_llm()` itself so the LangChain model and its `RateLimitedModel` wrapper are built once per process lifetime.

**Files:** `infra/rate_limit.py`, `infra/langchain_json.py`, `infra/chroma.py`

---

### 2. `query.py` → `query/` Package

The flat `query.py` is replaced by a small directory (same pattern as `recall/`), per codebase rule §3.

| File | Role |
|------|------|
| `_state.py` | `QueryState` TypedDict. `chunks` and `trace_parts` use `Annotated[list, operator.add]` so sub-query node outputs accumulate rather than overwrite. |
| `_breakdown.py` | LangGraph node. LLM decomposes the user query into ≤4 focused sub-queries. Always anchors to the original query as item 0. Falls back silently to `[query]` on any LLM failure — retrieval always runs. |
| `_search.py` | LangGraph node. Runs vector + lexical + recall evidence search for each sub-query independently. `finalize_chunks()` dedupes, re-ranks, and context-packs the merged set against the original query. |
| `_graph.py` | Compiles `START → breakdown → search → END` once at `QueryEvidenceChain` construction. |
| `__init__.py` | Public interface: `QueryEvidenceChain(json_client)`, `QueryAnswerChain`, `build_query_result`. Identical signatures to the old `query.py`. |

**Context engineering:** each chunk is reduced to its summary + the most query-relevant passages (≤3 snippets × ≤420 chars each) before being sent to the answer model. Per-sub-query pass budget prevents context window exhaustion across multiple passes.

---

### 3. `rag_service_impl.py`

One line: `QueryEvidenceChain()` → `QueryEvidenceChain(json_client)`.

---

### 4. Tests

- 2 new tests: breakdown fallback on LLM failure, cap + dedup behaviour.
- 2 existing query tests updated: `QueryJson` stub handles breakdown system call; `recall_key_count` now read from `sub_query_traces[0]` in the trace.
- **24/24 pass.**

---

### 5. Docs

- `server/docs/SEAI_RETRIEVAL_FLOW.md` — updated flow diagram, new `sub_queries` / `sub_query_traces` trace fields, context engineering note.
- `current-state.md` — updated retrieval description and weaknesses.

---

## What Did NOT Change

- `POST /api/retrieval/query` route — untouched.
- `QueryAnswerChain` — untouched.
- Response shape `{answer, citations, source_chunks, retrieval_trace}` — untouched (only additive trace fields).
- All repositories — untouched.
- Ingest pipeline — untouched.

---

## Retrieval Trace (new fields)

```json
"retrieval_trace": {
  "sub_queries": ["original query", "sub-query 1", "sub-query 2"],
  "sub_query_count": 3,
  "sub_query_traces": [
    {"sub_query": "...", "recall_key_count": 2, "source_chunk_count": 4},
    ...
  ],
  ...existing fields unchanged...
}
```

---

## Test Command

```bash
cd server && .venv/bin/python -m pytest src/services/rag/test_rag_service.py -v
```
