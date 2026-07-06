# The Indexing Engine

The indexing engine translates raw human notes into structured, retrievable vectors and entities. 

## Level 1: The Core Concept
At its most basic level, indexing is about chopping up a document and asking an LLM to explain what each piece means.

```mermaid
flowchart TD
    RAW["Raw Note"] --> SPLIT["Split into Source Chunks"]
    SPLIT --> CHUNK1["Chunk 1"]
    SPLIT --> CHUNK2["Chunk 2"]
    
    CHUNK1 -->|"LLM"| SUMM1["Summary"]
    CHUNK1 -->|"LLM"| KEYS1["Entities (Recall Keys)"]
    
    CHUNK2 -->|"LLM"| SUMM2["Summary"]
    CHUNK2 -->|"LLM"| KEYS2["Entities (Recall Keys)"]
```

## Level 2: Idempotency, Splitting & Caching
If a user fixes a single typo in a 10,000-word document, we cannot afford to pay OpenAI to re-summarize the 9,999 words that didn't change. 
First, we split text cleanly. By default, `SourceWindowChain` splits at `2600` characters, but it intelligently seeks out double newlines (`\n\n`) to ensure paragraphs (and therefore complete ideas) are not severed in half.
We then introduce strict hashing and Exact Caching for every chunk.

```mermaid
flowchart TD
    RAW["Raw Note"] --> HASH["Compute content_hash (SHA-256)"]
    HASH --> SPLIT["Split into Chunks\n(Seek \n\n boundaries)"]
    
    SPLIT --> CHUNK_HASH["Hash(Chunk Text + LLM Signature)"]
    CHUNK_HASH --> EXACT_CACHE{"Check Redis\nExact Cache"}
    
    EXACT_CACHE -->|"✅ HIT (1ms)"| SKIP["Return Cached\nSummaries & Keys"]
    EXACT_CACHE -->|"❌ MISS"| LLM["LLM Extracts\nSummaries & Keys"]
    
    LLM --> SAVE_CACHE["Save to Redis Cache"]
```

## Level 3: The 4-Layer Deduplication Guard
When the LLM hallucinates slightly different entities (e.g., "Python 3" and "Python"), we must prevent graph sprawl. The `RecallNormalizerChain` handles this strict deduplication:

```mermaid
flowchart TD
    LLM_KEYS["Raw LLM Recall Keys"] --> L1["1. Pre-prompt Candidate Retrieval\n(Extracts salient entities, runs concurrent FTS + Vector DB lookup)"]
    L1 --> L2["2. In-Memory Batch Merge\n(Normalizes terms within the same job)"]
    L2 --> L3["3. Exact-Match Repository Lookup\n(Merges new aliases into existing DB keys)"]
    L3 --> L4[/"4. SQLite Unique Constraints\n(Database-level lock prevention)"/]
    L4 --> FINAL["Save Canonical Recall Keys"]
```
*(Code fact: The Normalizer caps aliases at 10 items, strictly enforces string length limits, and if an exact match is ambiguous, it falls back to the normalized name match to ensure safe merging).*

## Level 4: The Code Reality (Durable LangGraph)
Because indexing takes time and APIs fail, the entire sequence is wrapped in a durable LangGraph state machine. Each step acts as a deterministic checkpoint.

```mermaid
flowchart TD
    START([LangGraph: DurableIngestRunner]) --> LOAD_RAW
    LOAD_RAW["node: load_raw_input\n(Fetch from SQLite)"] --> COND1
    
    COND1{"Abort?"} -->|"Yes"| ABORT["node: abort"]
    COND1 -->|"No"| SRC_CHUNKS
    
    SRC_CHUNKS["node: source_chunks\n(Split & Hash)"] --> RECALL
    
    RECALL["node: recall\n(Cache/LLM & Dedupe)"] --> REC_VEC
    
    REC_VEC["node: recall_vectors\n(Embed Keys to Chroma)"] --> SRC_VEC
    
    SRC_VEC["node: source_vectors\n(Embed Chunks & Materialize Lineage)"] --> COMP
    
    COMP["node: complete\n(Mark Job Done & Fire SSE)"] --> END([END])
```

Here is the exact Python implementation from `server/src/services/rag/private/durability/runner.py` showing how this graph is constructed in memory:

```python
    def _build_graph(self):
        """Build the fixed durable ingest workflow once per runner."""
        graph = StateGraph(IngestGraphState)
        graph.add_node("load_raw_input", self._load_raw_input)
        graph.add_node("source_chunks", self._source_chunk_node)
        graph.add_node("recall", self._recall_node)
        graph.add_node("recall_vectors", self._recall_vector_node)
        graph.add_node("source_vectors", self._source_vector_node)
        graph.add_node("complete", self._complete_node)
        graph.add_node("abort", self._abort_node)
        
        graph.add_edge(START, "load_raw_input")
        graph.add_conditional_edges("load_raw_input", self._after_load_raw_input, {"abort": "abort", "continue": "source_chunks"})
        graph.add_edge("source_chunks", "recall")
        graph.add_edge("recall", "recall_vectors")
        graph.add_edge("recall_vectors", "source_vectors")
        graph.add_edge("source_vectors", "complete")
        
        graph.add_edge("complete", END)
        graph.add_edge("abort", END)
        return graph.compile()
```

## Level 5: The Full Integrated Picture
Now that we have explained every component piece-by-piece, here is the brutal reality of the absolute, end-to-end Indexing flow integrating the DB, the LangGraph, the Checkpoints, the Embedding, the Cache, and the SSE fanout.

```mermaid
flowchart TD
    START([fa:fa-play POST /notes/]) --> SAVENOTE
    SAVENOTE["Save note to SQLite\nWrite event_outbox ('note.created')"] --> SUBMIT
    SUBMIT["RAG Listener consumes event via Redis Streams\nsubmit_ingest_job(job_id=note_id)"] --> APIRET

    APIRET([Return 200 OK to User])

    SUBMIT -.-> BGWORK
    BGWORK(["Background Ingest Job Starts (LangGraph workflow)"]) --> RAWINPUT

    RAWINPUT["Hash text → content_hash\nSave/reuse raw_input row"] --> CHK_RAW
    CHK_RAW[/"Checkpoint: raw_input"/] --> SPLIT

    SPLIT["Split raw_input into source windows\nSave as source_chunks\nCompute deterministic piece hash"] --> CHK_PIECE
    CHK_PIECE[/"Checkpoint: source_piece"/] --> CHUNK_LOOP

    CHUNK_LOOP([▼ Loop over each source_chunk]) --> CACHE_SUMM

    CACHE_SUMM[/"Exact Cache: SourceChunkDraftChain\nKey: SHA256(text) + llm_sig"/] --> SUMM_Q

    SUMM_Q{"Summary\nCached?"} -->|"✅ HIT"| CACHE_REC
    SUMM_Q -->|"❌ MISS"| LLM_SUMM

    LLM_SUMM["LLM: Generate neutral summary\nSave to Exact Cache"] --> CACHE_REC

    CACHE_REC[/"Exact Cache: RecallDraftChain\nKey: SHA256(text) + llm_sig"/] --> REC_Q

    REC_Q{"Entities\nCached?"} -->|"✅ HIT"| DEDUPE
    REC_Q -->|"❌ MISS"| LLM_REC

    LLM_REC["LLM: Extract Recall Keys\nSave to Exact Cache"] --> DEDUPE

    DEDUPE["Deduplicate (4 layers)\nSave/update recall_keys\nAppend recall_links"] --> CHK_REC
    CHK_REC[/"Checkpoint: recall_chunk"/] --> NEXT_CHUNK

    NEXT_CHUNK([Proceed to Vectors]) --> EMBED
    EMBED["Embed source_chunks & recall_keys\nvia configured embedding model"] --> CHROMA
    CHROMA[/"Upsert to ChromaDB collections:\n- source_chunks\n- recall_keys"/] --> CHK_VEC

    CHK_VEC[/"Checkpoint:\n- source_vector\n- recall_key_vector"/] --> LINEAGE

    LINEAGE["Lineage Materialization\nParse note directory path (/A/B/C/)\nInject 'dir_A: True', 'dir_B: True'\ninto ChromaDB metadata"] --> SSE_PUB

    SSE_PUB["Publish ingest_job.changed to SSE"] --> FINISH

    FINISH["Mark Job Complete"] --> DONE
    DONE([Ingest Finished])
```
