from __future__ import annotations

import sqlite3
from pathlib import Path

from src.infra.settings import get_user_embedding_setting_candidates, get_user_llm_setting_candidates, get_user_setting_candidates
from src.infra import retrieval_cache
from src.repositories import config_presets, config_profiles


def _db(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    schema = Path(__file__).resolve().parents[2] / "resources" / "schema.sql"
    conn.executescript(schema.read_text())
    conn.execute("INSERT INTO users (id, identifier, password_hash) VALUES ('user-1', 'u', 'h')")
    monkeypatch.setattr(config_presets, "get_connection", lambda: conn)
    monkeypatch.setattr(config_profiles, "get_connection", lambda: conn)
    get_user_setting_candidates.cache_clear()
    get_user_llm_setting_candidates.cache_clear()
    get_user_embedding_setting_candidates.cache_clear()
    return conn


def test_processing_settings_do_not_override_config_models(monkeypatch):
    _db(monkeypatch)
    config_presets.save({
        "name": "lane-a",
        "llm_model": "gpt-a",
        "llm_api_key": "secret-a",
        "embedding_model": "embed-lane",
        "chunk_size": 111,
    }, "user-1")
    config_presets.save_processing({
        "embedding_batch_size": 12,
        "chunk_size": 900,
        "chunk_overlap": 90,
        "ingest_retry_backoff_seconds": "1,2,3",
    }, "user-1")

    settings = get_user_setting_candidates("user-1")[0]

    assert settings.llm_model == "gpt-a"
    assert settings.embedding_model == "embed-lane"
    assert settings.embedding_batch_size == 12
    assert settings.chunk_size == 900
    assert settings.chunk_overlap == 90
    assert "api_key" not in settings.rotation_snapshot()


def test_rotation_candidates_keep_saved_order_without_persisted_pointer(monkeypatch):
    _db(monkeypatch)
    first = config_presets.save({"name": "first", "llm_model": "gpt-first"}, "user-1")
    second = config_presets.save({"name": "second", "llm_model": "gpt-second"}, "user-1")
    config_presets.save_rotation_config("user-1", True, [second, first])

    before = config_presets.get_rotation_config("user-1")
    candidates = get_user_setting_candidates("user-1")
    after = config_presets.get_rotation_config("user-1")

    assert [item.preset_name for item in candidates] == ["second", "first"]
    assert before == after


def test_llm_and_embedding_rotation_are_independent(monkeypatch):
    _db(monkeypatch)
    first = config_presets.save({"name": "first", "llm_model": "gpt-first", "embedding_model": "embed-first"}, "user-1")
    second = config_presets.save({"name": "second", "llm_model": "gpt-second", "embedding_model": "embed-second"}, "user-1")

    config_presets.save_split_rotation_config(
        "user-1",
        llm_enabled=True,
        llm_preset_ids=[second, first],
        embedding_enabled=False,
        embedding_preset_ids=[first, second],
        llm_active_preset_id=first,
        embedding_active_preset_id=first,
    )

    assert [item.preset_name for item in get_user_llm_setting_candidates("user-1")] == ["second", "first"]
    embedding = get_user_embedding_setting_candidates("user-1")[0]
    assert embedding.preset_name == "first"
    assert embedding.embedding_model == "embed-first"


def test_activating_specific_config_disables_rotation(monkeypatch):
    _db(monkeypatch)
    first = config_presets.save({"name": "first"}, "user-1")
    second = config_presets.save({"name": "second"}, "user-1")
    config_presets.save_rotation_config("user-1", True, [first, second])

    assert config_presets.set_active(second, "user-1")

    assert config_presets.get_rotation_config("user-1")["enabled"] == 0
    assert config_presets.get_rotation_config("user-1")["llm"]["enabled"] is False
    assert config_presets.get_rotation_config("user-1")["embedding"]["enabled"] is False
    assert get_user_setting_candidates("user-1")[0].preset_name == "second"


def test_stage_specific_llm_config_resolution(monkeypatch):
    _db(monkeypatch)
    fast = config_profiles.save_llm({"name": "fast", "llm_model": "gpt-fast"}, "user-1")
    smart = config_profiles.save_llm({"name": "smart", "llm_model": "gpt-smart"}, "user-1")

    config_profiles.save_stage("user-1", "retrieval.query_breakdown", "llm", False, [], fast)
    config_profiles.save_stage("user-1", "retrieval.answer", "llm", False, [], smart)

    assert get_user_llm_setting_candidates("user-1", "retrieval.query_breakdown")[0].llm_model == "gpt-fast"
    assert get_user_llm_setting_candidates("user-1", "retrieval.answer")[0].llm_model == "gpt-smart"


def test_stage_rotation_is_isolated(monkeypatch):
    _db(monkeypatch)
    first = config_profiles.save_llm({"name": "first", "llm_model": "gpt-first"}, "user-1")
    second = config_profiles.save_llm({"name": "second", "llm_model": "gpt-second"}, "user-1")

    config_profiles.save_stage("user-1", "retrieval.verifier", "llm", True, [second, first], first)
    config_profiles.save_stage("user-1", "retrieval.answer", "llm", False, [], first)

    assert [item.llm_model for item in get_user_llm_setting_candidates("user-1", "retrieval.verifier")] == ["gpt-second", "gpt-first"]
    assert [item.llm_model for item in get_user_llm_setting_candidates("user-1", "retrieval.answer")] == ["gpt-first"]


def test_stage_signature_changes_with_config(monkeypatch):
    _db(monkeypatch)
    first = config_profiles.save_llm({"name": "first", "llm_model": "gpt-first"}, "user-1")
    second = config_profiles.save_llm({"name": "second", "llm_model": "gpt-second"}, "user-1")

    config_profiles.save_stage("user-1", "retrieval.answer", "llm", False, [], first)
    before = retrieval_cache.llm_settings_signature("user-1", "retrieval.answer")
    config_profiles.save_stage("user-1", "retrieval.answer", "llm", False, [], second)
    after = retrieval_cache.llm_settings_signature("user-1", "retrieval.answer")

    assert before != after
