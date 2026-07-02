# SSE Infrastructure

Server-Sent Events push job and retrieval progress to the frontend.

## Shape

The SSE system is defined by a small protocol in `src/infra/sse/models.py`.

```python
class SseService(Protocol):
    async def publish(self, topic: str, event: str, data: dict[str, Any]) -> None: ...
    async def subscribe(self, topic: str) -> AsyncGenerator[ServerSentEvent, None]: ...
```

Application code publishes to topics and does not know how clients are connected.

## Implementation

Docker uses `RedisSseService`:

- live HTTP/SSE sockets stay process-local
- Redis Pub/Sub broadcasts topic events across server instances
- each instance forwards matching events only to its local sockets
- Redis stores connection presence metadata with TTL

Manual backend runs without `REDIS_URL` use `MemorySseService`:

- one `asyncio.Queue` per connected client
- queue removed on disconnect
- single-process only

SSE Pub/Sub is volatile display fanout. Durable job state remains in SQLite.

## RAG Usage

RAG code depends on `ProgressReporter`, not `SseService`.

```python
class ProgressReporter(Protocol):
    async def report(self, message: str, details: dict[str, Any] | None = None) -> None: ...
```

`src/routes/retrieval.py` adapts SSE to this protocol for request-scoped progress.

Retrieval progress events use the same nested display shape as ingest jobs:

```json
{
  "message": "Sub-query 1/3: searching focused evidence.",
  "depth": 2,
  "ref": "retrieval:search:1",
  "parent_ref": "retrieval:search",
  "details": {
    "sub_query": "focused query"
  }
}
```

`message`, `depth`, and `ref` are top-level display fields. Extra diagnostic values stay under `details` so the Ask UI can render a compact indented trace without dumping raw JSON.

Durable ingest emits a domain event (`ingest_job.changed`) after job-row changes. `src/services/rag/private/durability/events.py` bridges that event to SSE and publishes on `ingest_jobs:{user_id}`.

See `server/docs/REDIS_EVENTS.md` for Redis Pub/Sub fanout and presence details.
