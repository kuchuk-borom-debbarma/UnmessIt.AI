# UnmessIt.AI: Core Architectural Vision & Design Decisions

This document captures the foundational design philosophy and key architectural decisions behind UnmessIt.AI. It serves as the baseline specification for understanding the system's intent.

## 1. High-Level Vision
UnmessIt.AI is an advanced Retrieval-Augmented Generation (RAG) application. It was built to solve the problem of ingesting disparate notes and enabling an AI to reason across them cohesively. 
A key requirement is a **Backend-Driven UI**—the frontend should be highly dynamic and controlled by state updates pushed from the backend.

## 2. The Core Problem: Why Not Naive RAG or Graph RAG?
- **Naive RAG is insufficient**: It blindly chops documents into isolated chunks. If one chunk contains context and another contains the answer, Naive RAG fails to connect them.
- **Graph RAG is overly complex**: While Graph RAG connects entities, it struggles with user-generated unstructured text. It introduces severe *idempotency* issues (e.g., merging "Newton" and "Isaac Newton" across 10,000 documents) and scaling costs. Adding chunk references directly into the graph creates unmanageable complexity.
- **Alternative Approaches**: Techniques like RAPTOR and ColBERT were evaluated but dismissed due to excessive storage consumption or requiring massive context windows.

## 3. The UnmessIt.AI Solution: "Recall Keys"
UnmessIt.AI implements a highly optimized, localized version of Graph RAG tailored for small, local LLMs.
Instead of building a rigid global graph, we rely on **Chunks** and **Recall Keys**:
1. Documents are split into chunks.
2. The LLM extracts entities/topics ("Recall Keys") from each chunk.
3. A link is created between the Recall Key and the Source Chunk.

**Example**: 
If Chunk A discusses "Why Java is bad", it produces the Recall Key `Java`. If Chunk B also discusses "Java", it produces the same Recall Key `Java`. The chunks are now implicitly connected without needing a massive graph database structure. 
This is faster, simpler, and explicitly designed to work with limited context windows, preventing "lost in the middle" degradation.

## 4. Key Constraints & Features
- **Incremental & Modular Indexing**: The system is designed for environments where documents are frequently added or updated. If Document B is added, only Document B is processed, avoiding expensive re-indexing of previously ingested documents.
- **Durable Ingestion**: Indexing is built to be resilient. If an API key hits a rate limit or the application crashes, the ingestion pipeline will resume exactly where it left off.
- **Intelligent Caching**: Retrieval utilizes aggressive caching to minimize LLM calls, reducing API costs and latency.

## 5. Future Upgrades
- **Contextual Chunk Resolution**: If a chunk's meaning is lost due to splitting, a future LLM judge can detect missing context and dynamically pull in previous chunks or their Recall Keys/Links to restore meaning on the fly.