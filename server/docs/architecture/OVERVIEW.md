# Architecture Overview

UnmessIt.AI is not a standard vector database application. We do not simply embed documents and perform naive similarity searches. Standard Retrieval-Augmented Generation (RAG) fails on complex reasoning because it loses the relationship between ideas. 

UnmessIt solves this by building a highly interconnected **Knowledge Graph** on top of text chunks.

## 1. Chunking with Overlaps
Documents are chunked using `SourceWindowChain`. We enforce strict character limits (e.g. 2600 chars), but crucially, these chunks **overlap**. This ensures that an idea spanning across a boundary isn't abruptly severed, preserving context for the extraction phase.

## 2. Recall Keys & Links
Instead of generating generic summaries of each chunk, we force the LLM to extract highly specific nouns, concepts, and subjects. 
These become **Recall Keys** (nodes). 
We then create **Recall Links** (edges) connecting the Recall Key back to the original Source Chunk. 

If the entity "PostgreSQL" is mentioned in Chunk 1 and Chunk 42, a single "PostgreSQL" Recall Key acts as a central bridge connecting those disparate parts of the document.

## 3. Graph Navigation (Querying)
During querying, we decompose questions and search for specific **Recall Keys** first. 
Because the Recall Keys are interconnected hubs, finding the right Key instantly gives us direct, hard-linked pointers to every relevant Source Chunk that mentioned it, scattered across thousands of documents. 
This graph traversal allows for incredible accuracy and prevents the LLM from hallucinating answers based on loosely-related semantic noise.
