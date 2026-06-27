# UnmessIt.AI Codebase Rules

These rules describe the active server architecture. Keep it boring, small, and easy to change.

## 1. Shape Of The Server
- `src/main.py` owns app creation, DB init, logging setup, DI bootstrap, routers, and lifespan tasks.
- `src/routes/` is HTTP delivery only: validate input, resolve a port/service/repository from `kink`, call it, return the result.
- `src/services/` owns use-case orchestration and domain flow. It should not know vendor SDKs or storage details.
- `src/repositories/` owns SQLite query/write classes and repository ports.
- `src/infra/` owns concrete external technology: LangChain, Chroma, SQLite connection, settings, logging, UUIDs, and event bus adapters.
- `src/ports/` owns shared cross-service ports such as `JsonLLM` and `EventBus`.
- Tests may import concrete infra adapters when they are testing the adapter itself.

## 2. Ports And Adapters
- Domain/application code depends on ports, simple models, and injected collaborators.
- Use a shared port in `src/ports/` when multiple services need the same capability.
- Use a service-local port when the contract belongs to one service boundary only.
- Put repository ports in `src/repositories/ports/` when they describe storage access.
- Concrete adapter names should make the technology obvious, e.g. `Sqlite...`, `Chroma...`, `LLMJsonClient`, `InMemoryEventBus`.
- Do not hide concrete adapters behind another factory module. Wire them in DI.

## 3. Dependency Injection
- `src/infra/di/bootstrap.py` is the only composition root.
- Active wiring goes through `kink`.
- Routes, listeners, and domain services must not construct SQLite, Chroma, LangChain, event bus, or repository adapters.
- Constructor injection is preferred for service collaborators.
- Factories are allowed only in `src/infra/di/bootstrap.py` or temporary compatibility shims.
- If a dependency is optional for tests, pass a fake explicitly instead of adding fallback construction inside the service.

## 4. LangChain And LLMs
- LangChain imports belong only in `src/infra/langchain/`.
- Services use the `JsonLLM` port and receive an injected client.
- Planner, reranker, answer generator, and SEAI chains may write prompts, but they must not import LangChain classes directly.
- JSON parsing and repair belongs in the infra JSON client, not copied into each chain.
- Do not log API keys, full prompts, full model responses, or full raw source text.

## 5. Event Bus
- Use the `EventBus` port from `src/ports/event_bus.py`.
- The active adapter is `InMemoryEventBus`, registered in DI.
- Do not add global event bus singletons.
- Routes publish jobs; listener adapters subscribe and call use cases.
- The in-memory bus is enough until multiple processes or durable delivery are required.

## 6. Ingest Engine
- `services/ingest_engine` follows `ports/`, `adapters/`, and `domain/`.
- `ports/inbound/ingestor.py` is the public ingest use-case contract.
- `adapters/inbound/listener.py` translates event bus messages into `Ingestor.ingest(...)`.
- `domain/seai/ingestor.py` defines the SEAI chain order. Do not create a separate SEAI factory.
- SEAI chains implement a tiny `run(...)` protocol and stay independently swappable.
- Keep SEAI chain files single-purpose: window, split, summarize, verify episode, extract atoms, verify atoms, code verify atoms.
- Raw input is saved before LLM work so spans always point to durable truth.

## 7. Retrieval Engine
- `DeterministicRetrievalService` owns retrieval orchestration only.
- Keep retrieval substeps isolated: planner, evidence cards, reranker, quote-bank packing, answer generation, citation validation.
- Retrieval must keep the public response shape: `{ answer, citations, retrieval_trace }`.
- Broad retrieval may use vector search plus lexical/entity sweep, then pack only relevant quote-bank evidence.
- Citation validation must stay source-bound: cited quotes must come from atom evidence spans or episode spans.
- Do not add graph traversal, atom links, or global synthesis unless `SEAI_RETRIEVAL_FLOW.md` is updated first.

## 8. Repositories And Vectors
- SQLite access goes through repositories under `src/repositories/`.
- Chroma access goes through vector adapters under `src/infra/vector/`.
- Wipe behavior must clear SEAI tables, legacy `memory_items`, raw inputs, and Chroma.
- Keep legacy table support only where needed for old DB/wipe compatibility.
- New repository contracts should live in `src/repositories/ports/`.

## 9. Routes And Dev Endpoints
- Routes contain no SQL and no business logic.
- `POST /ingest/`, `POST /api/retrieval/query`, `GET /dev/seai`, and `DELETE /dev/facts` are stable public/dev contracts.
- Dev routes may resolve dev-only repositories directly from DI until a dev port is useful.
- If route logic grows past request/response plumbing, move it into a service or repository.

## 10. SEAI Product Rules
- Raw input is the source of truth.
- Episodes may have multiple spans from one raw input.
- Atoms must be complete standalone claims with exact evidence spans.
- Direct atoms describe facts; relation atoms describe causality, motivation, contrast, sequence, or relationships.
- Annotations should stay generic and domain-neutral.
- Retrieval context must stay compact: selected quote bank first, nearby/broad evidence only when useful.

## 11. Logging And Comments
- Logs should show lifecycle, IDs, counts, span ranges, and short previews when useful.
- Never log secrets, API keys, full raw inputs, full prompts, full model responses, or full evidence banks.
- Comments explain why a non-obvious choice exists. Do not narrate obvious code.
- Use `ponytail:` comments for deliberate shortcuts and name the upgrade path.

## 12. Cleanup Rules
- Delete inactive experiments instead of wrapping them.
- Do not add `private` or `public` folders when `ports`, `adapters`, and `domain` describe the boundary.
- Do not add interfaces for imaginary future implementations.
- Do not add dependencies for work the stdlib or existing packages already cover.
- Add one focused test for non-trivial logic or an architecture boundary.

## 13. Known Intentional Debt
- Retrieval repository/vector ports still live under `services/retrieval_engine/ports/outbound/`. Move repository ports to `src/repositories/ports/` and vector ports to a shared/vector port only when touching those files next.
- Dev routes resolve `SqliteDevRepository` directly. Keep it until dev behavior grows or a second dev repository exists.
- Legacy `memory_items` compatibility remains because wipe and old DBs still need it.
