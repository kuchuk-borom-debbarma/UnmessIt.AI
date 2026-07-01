import pytest

from src.infra.sqlite import get_connection
from src.repositories import raw_inputs
from src.services.rag.private.durability import repository
from src.services.rag.private.durability.repository import IngestPaused
from src.services.rag.private.durability.models import (
    CHECKPOINT_COMPLETE,
    CHECKPOINT_FAILED,
    STATUS_ABORTED,
    STATUS_COMPLETE,
    STATUS_FAILED,
    STATUS_PAUSED,
    STATUS_QUEUED,
    STATUS_RUNNING,
    STATUS_WAITING_RETRY,
)


def setup_function():
    conn = get_connection()
    conn.execute("DELETE FROM event_handler_runs")
    conn.execute("DELETE FROM event_outbox")
    conn.execute("DELETE FROM ingest_checkpoints")
    conn.execute("DELETE FROM ingest_jobs")
    conn.execute("DELETE FROM raw_inputs")
    conn.execute("DELETE FROM notes")
    conn.execute("DELETE FROM users")
    conn.execute("INSERT INTO users (id, identifier, password_hash) VALUES ('user-1', 'user', 'hash')")
    conn.commit()


def _job(job_id="job-1", text="hello", content_hash="hash-1"):
    raw_id = raw_inputs.save(job_id, text, "user-1", content_hash)
    return repository.create_or_reuse_job(job_id, content_hash, raw_id)


def test_create_reuse_list_and_raw_input_update(monkeypatch):
    monkeypatch.setattr(repository, "redis_enabled", lambda: False)
    job = _job()
    assert job["status"] == STATUS_QUEUED
    assert repository.get_by_hash("hash-1")["id"] == "job-1"
    assert repository.create_or_reuse_job("other", "hash-1", job["raw_input_id"])["id"] == "job-1"

    raw_2 = raw_inputs.save("job-raw-2", "new raw", "user-1", "hash-raw-2")
    repository.set_raw_input("job-1", raw_2)
    assert repository.get("job-1")["raw_input_id"] == raw_2
    assert repository.list_jobs()["total"] == 1
    assert repository.list_jobs("user-1")["data"][0]["id"] == "job-1"


def test_stage_retry_pause_resume_abort_and_delete(monkeypatch):
    monkeypatch.setattr(repository, "redis_enabled", lambda: False)
    _job()

    repository.start_stage("job-1", "source_chunks")
    assert repository.get("job-1")["status"] == STATUS_RUNNING

    retry = repository.schedule_retry("job-1", "source_chunks", "unit-1", "boom", [0])
    assert retry["status"] == STATUS_WAITING_RETRY
    assert retry["metadata"]["failed_unit_key"] == "unit-1"
    assert repository.list_resumable_jobs()[0]["id"] == "job-1"

    repository.pause("job-1")
    assert repository.get("job-1")["status"] == STATUS_PAUSED
    repository.resume("job-1")
    assert repository.get("job-1")["status"] == STATUS_QUEUED

    repository.abort("job-1", "missing source", {"why": "test"})
    aborted = repository.get("job-1")
    assert aborted["status"] == STATUS_ABORTED
    assert aborted["metadata"]["why"] == "test"

    raw_2 = raw_inputs.save("job-2", "hello", "user-1", "hash-2")
    requeued = repository.create_or_reuse_job("job-2", "hash-1", raw_2)
    assert requeued["status"] == STATUS_QUEUED

    assert repository.delete_job("job-1") is True
    assert repository.delete_job("missing") is False


def test_retry_limit_complete_metadata_and_checkpoints(monkeypatch):
    monkeypatch.setattr(repository, "redis_enabled", lambda: False)
    _job()

    failed = None
    for _ in range(5):
        failed = repository.schedule_retry("job-1", "recall", "unit-1", "boom", [0])
    assert failed["status"] == STATUS_FAILED
    repository.reset_attempts("job-1")
    assert repository.get("job-1")["attempt_count"] == 0

    repository.update_metadata("job-1", {"count": 1})
    assert repository.get("job-1")["metadata"]["count"] == 1
    repository.update_metadata("missing", {"count": 2})
    repository.update_metadata("job-1", {})

    repository.start_checkpoint("job-1", "source", "unit-1")
    repository.complete_checkpoint("job-1", "source", "unit-1", "out", {"ok": True})
    assert repository.checkpoint_complete("job-1", "source", "unit-1") is True
    assert repository.has_stage_checkpoints("job-1", "source") is True
    assert repository.checkpoint("job-1", "source", "unit-1")["status"] == CHECKPOINT_COMPLETE

    repository.fail_checkpoint("job-1", "source", "unit-2", "bad")
    assert repository.checkpoint("job-1", "source", "unit-2")["status"] == CHECKPOINT_FAILED

    repository.complete("job-1", {"done": True, "progress_message": "done"})
    complete = repository.get("job-1")
    assert complete["status"] == STATUS_COMPLETE
    assert complete["metadata"]["done"] is True

    repository.clear_all()
    assert repository.list_jobs()["total"] == 0


def test_waiting_retry_reuse_resumes_existing_job(monkeypatch):
    monkeypatch.setattr(repository, "redis_enabled", lambda: False)
    job = _job()
    repository.schedule_retry("job-1", "source", "unit-1", "boom", [60])
    assert repository.get("job-1")["status"] == STATUS_WAITING_RETRY

    reused = repository.create_or_reuse_job("other", "hash-1", job["raw_input_id"])

    assert reused["id"] == "job-1"
    assert reused["status"] == STATUS_QUEUED


def test_paused_jobs_do_not_start_or_retry(monkeypatch):
    monkeypatch.setattr(repository, "redis_enabled", lambda: False)
    _job()
    repository.pause("job-1")

    with pytest.raises(IngestPaused):
        repository.start_stage("job-1", "source")
    with pytest.raises(IngestPaused):
        repository.start_checkpoint("job-1", "source", "unit-1")

    same = repository.schedule_retry("job-1", "source", "unit-1", "boom", [0])
    assert same["status"] == STATUS_PAUSED


def test_progress_only_metadata_and_bad_json_fallback(monkeypatch):
    monkeypatch.setattr(repository, "redis_enabled", lambda: False)
    progress = []
    monkeypatch.setattr(repository, "_publish_progress", lambda job_id, value: progress.append((job_id, value)))
    _job()

    repository.update_metadata("job-1", {"progress_message": "halfway"})

    assert progress == [("job-1", "halfway")]
    assert repository.get("job-1")["metadata"] == {}

    conn = get_connection()
    conn.execute("UPDATE ingest_jobs SET metadata = ? WHERE id = ?", ("{", "job-1"))
    conn.execute(
        "INSERT INTO ingest_checkpoints (job_id, stage, unit_key, status, metadata) VALUES (?, ?, ?, ?, ?)",
        ("job-1", "source", "bad-json", CHECKPOINT_COMPLETE, "{"),
    )
    conn.commit()

    assert repository.get("job-1")["metadata"] == {}
    assert repository.checkpoint("job-1", "source", "bad-json")["metadata"] == {}


def test_publish_helpers_swallow_sse_errors(monkeypatch):
    def bad_changed(_job_id):
        raise RuntimeError("changed down")

    def bad_progress(_job_id, _progress):
        raise RuntimeError("progress down")

    import src.services.rag.private.durability.events as events

    monkeypatch.setattr(events, "publish_job_changed", bad_changed)
    monkeypatch.setattr(events, "publish_job_progress", bad_progress)

    repository._publish_changed("job-1")
    repository._publish_progress("job-1", "working")
