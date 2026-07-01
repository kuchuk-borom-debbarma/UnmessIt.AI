from src.infra.sqlite import get_connection
from src.repositories import event_outbox
from src.repositories import raw_inputs
from src.services.rag.private.durability import repository as durability_repo


def setup_function():
    conn = get_connection()
    conn.execute("DELETE FROM event_handler_runs")
    conn.execute("DELETE FROM event_outbox")
    conn.execute("DELETE FROM ingest_checkpoints")
    conn.execute("DELETE FROM ingest_jobs")
    conn.execute("DELETE FROM raw_inputs")
    conn.execute("DELETE FROM users")
    conn.execute("INSERT INTO users (id, identifier, password_hash) VALUES ('user-1', 'user', 'hash')")
    conn.commit()


def test_outbox_insert_dedupes_by_idempotency_key():
    first = event_outbox.enqueue("note.created", "note.created", {"note_id": "n1"}, "note.created:n1")
    second = event_outbox.enqueue("note.created", "note.created", {"note_id": "n1"}, "note.created:n1")

    rows = get_connection().execute("SELECT * FROM event_outbox").fetchall()
    assert first == second
    assert len(rows) == 1


def test_outbox_publish_status_transitions():
    event_id = event_outbox.enqueue("note.created", "note.created", {"note_id": "n1"})

    event_outbox.mark_failed(event_id)
    assert event_outbox.pending()[0]["status"] == event_outbox.STATUS_FAILED

    event_outbox.mark_published(event_id)
    row = get_connection().execute("SELECT status, attempts, published_at FROM event_outbox WHERE id = ?", (event_id,)).fetchone()
    assert row["status"] == event_outbox.STATUS_PUBLISHED
    assert row["attempts"] == 2
    assert row["published_at"]


def test_handler_idempotency_skips_completed_duplicate():
    event_id = event_outbox.enqueue("note.created", "note.created", {"note_id": "n1"})

    assert event_outbox.begin_handler(event_id, "handler") is True
    event_outbox.complete_handler(event_id, "handler")
    assert event_outbox.begin_handler(event_id, "handler") is False


def test_fail_handler_and_bad_payload_fallback():
    event_id = event_outbox.enqueue("note.created", "note.created", {"note_id": "n1"})
    assert event_outbox.begin_handler(event_id, "handler") is True
    event_outbox.fail_handler(event_id, "handler", "bad")
    row = get_connection().execute(
        "SELECT status, error FROM event_handler_runs WHERE event_id = ? AND handler_name = 'handler'",
        (event_id,),
    ).fetchone()
    assert row["status"] == event_outbox.STATUS_FAILED
    assert row["error"] == "bad"

    conn = get_connection()
    conn.execute(
        "UPDATE event_outbox SET status = ?, payload = ? WHERE id = ?",
        (event_outbox.STATUS_PENDING, "{", event_id),
    )
    conn.commit()
    assert event_outbox.pending()[0]["payload"] == {}


def test_ingest_job_change_records_outbox_in_redis_mode(monkeypatch):
    monkeypatch.setattr(durability_repo, "redis_enabled", lambda: True)
    raw_id = raw_inputs.save("job-1", "hello", "user-1", "hash-1")

    durability_repo.create_or_reuse_job("job-1", "hash-1", raw_id)

    row = get_connection().execute("SELECT topic, payload FROM event_outbox").fetchone()
    assert row["topic"] == "ingest_job.changed"
    assert "job-1" in row["payload"]


def test_ingest_job_rolls_back_when_outbox_enqueue_fails(monkeypatch):
    monkeypatch.setattr(durability_repo, "redis_enabled", lambda: True)

    def fail_enqueue(*args, **kwargs):
        raise RuntimeError("outbox down")

    monkeypatch.setattr(durability_repo.event_outbox, "enqueue", fail_enqueue)
    raw_id = raw_inputs.save("job-1", "hello", "user-1", "hash-1")

    try:
        durability_repo.create_or_reuse_job("job-1", "hash-1", raw_id)
    except RuntimeError:
        pass

    row = get_connection().execute("SELECT id FROM ingest_jobs WHERE id = 'job-1'").fetchone()
    assert row is None
