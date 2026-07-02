# Redis Events And SSE

Docker installs run Redis as the shared delivery layer. Manual backend runs may leave `REDIS_URL` unset and use in-memory delivery.

## Runtime Pieces

- `src/infra/redis.py`: cached Redis client and small JSON TTL helpers.
- `src/infra/events/redis_stream.py`: Redis Streams event bus.
- `src/infra/sse/redis_sse.py`: Redis Pub/Sub SSE fanout.
- `src/repositories/event_outbox.py`: SQLite outbox and handler idempotency rows.

SQLite remains the source of truth. Redis is a delivery and presence layer.

## Transactional Outbox

State changes that need cross-process delivery write an `event_outbox` row in the same SQLite transaction as the domain change.

Current transactional event sources:

- note lifecycle events
- ingest job change events

The dispatcher publishes pending rows to Redis Stream `unmessit:events` in small batches. When Redis is unavailable, rows remain pending or failed and are retried by the dispatcher loop.

## At-Least-Once Delivery

Consumers use Redis consumer group `unmessit:server`.

Flow:

```txt
event_outbox pending row
-> XADD unmessit:events
-> mark outbox row published
-> XREADGROUP by one server process
-> handler idempotency check
-> handler runs
-> XACK after success
```

Stale pending stream entries are reclaimed with `XAUTOCLAIM`. Duplicate stream entries or redelivery are safe because `event_handler_runs` records completed `(event_id, handler_name)` pairs.

Ordering is not a correctness rule. Handlers must remain idempotent.

## SSE Fanout

SSE HTTP connections stay in the process that accepted them. Redis does not store sockets.

`RedisSseService` publishes each event to a Redis Pub/Sub topic. Every server process listens, filters to topics with local subscribers, and forwards matching events to local queues.

Connection presence is stored in Redis with a short TTL:

```txt
unmessit:sse:connections:{connection_id}
```

Presence records include the instance id, connection id, topic, and last-seen timestamp. They are for observability and future routing work, not for moving live connections.

## Docker And Local Development

Docker compose sets:

```txt
REDIS_URL=redis://redis:6379/0
```

For manual local backend runs:

- leave `REDIS_URL` unset for in-memory events/SSE
- set `REDIS_URL=redis://localhost:6379/0` to test Redis Streams and Pub/Sub locally

Redis is not used for LLM response caching in this feature.
