# Supporting Systems

Running massive AI jobs in background workers requires network durability. If a server crashes mid-job, data cannot be lost.

## 1. The Transactional Outbox
We never save a note without guaranteeing it gets indexed.
```mermaid
flowchart LR
    API["API Request"] --> TX["BEGIN SQLITE TX"]
    TX --> SAVE_NOTE["Insert Note"]
    SAVE_NOTE --> SAVE_EVENT["Insert event_outbox ('note.created')"]
    SAVE_EVENT --> COMMIT["COMMIT TX"]
```

## 2. Redis Streams Dispatch
The outbox events are dispatched to a Redis Stream where worker processes consume them using a Consumer Group.
```mermaid
flowchart LR
    OUTBOX[(SQLite event_outbox)] --> DISPATCH["Dispatcher Loop"]
    DISPATCH --> REDIS[("Redis Stream\n'unmessit:events'")]
    REDIS -->|Consumer Group| WORKER["Worker Process"]
```

### The Real Code Implementation
Here is the exact `XREADGROUP` consumer loop from `server/src/infra/events/redis_stream.py`:

```python
    async def _consume_messages(self, client) -> None:
        messages = await client.xreadgroup(
            GROUP,
            self._consumer,
            {STREAM: ">"},
            count=CONSUME_BATCH,
            block=BLOCK_MS,
        )
        for _, entries in messages or []:
            for redis_id, fields in entries:
                if await self._handle(fields):
                    # Only acknowledge if handler succeeded or safely skipped
                    await client.xack(STREAM, GROUP, redis_id)
```

## 3. Strict Handler Idempotency
Because Redis Streams guarantees *at-least-once* delivery, a worker might receive the same event twice. We block this at the database level so a Note isn't indexed twice.
```mermaid
flowchart TD
    WORKER["Worker receives event"] --> CHK_IDEMP{"Check SQLite:\nevent_handler_runs"}
    
    CHK_IDEMP -->|"✅ Row Exists\n(event_id + handler_name)"| SKIP["Skip execution"]
    SKIP --> XACK["Send XACK to Redis"]
    
    CHK_IDEMP -->|"❌ Not Found"| EXECUTE["Execute Job"]
    EXECUTE --> SAVE_RUN["Insert into event_handler_runs"]
    SAVE_RUN --> XACK
```

## 4. The SSE Infrastructure

While Redis Streams manages durable jobs, we need a volatile, high-speed way to push UI progress updates (e.g., "Indexing 50% complete", "Sub-query 1/3 searching...").

### The Problem
WebSockets and SSE connections are held in the memory of the specific server process the user connected to.
```mermaid
flowchart TD
    WORKER_A["Worker A\n(Doing the indexing)"] -.->|How to send?| WORKER_B["Worker B\n(Holds user's SSE socket)"]
```

### Redis Pub/Sub Fanout
We use Redis Pub/Sub to broadcast the update to all servers. The server that owns the socket forwards it to the user.
```mermaid
flowchart TD
    WORKER_A["Worker A"] -->|Publishes| REDIS_PUB[/"Redis Pub/Sub Topic:\n'unmessit:sse:topics:ingest_jobs'"/]
    
    REDIS_PUB -->|Broadcasts to all| WORKER_B["Worker B"]
    REDIS_PUB -->|Broadcasts to all| WORKER_C["Worker C"]
    
    WORKER_B --> CHK_B{"Does B hold\nuser socket?"}
    CHK_B -->|"✅ Yes"| QUEUE["Client asyncio.Queue"]
    QUEUE --> BROWSER["User Browser"]
    
    WORKER_C --> CHK_C{"Does C hold\nuser socket?"}
    CHK_C -->|"❌ No"| DROP["Drop Message"]
```
