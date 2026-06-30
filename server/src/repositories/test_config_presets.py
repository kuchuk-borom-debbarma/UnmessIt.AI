from __future__ import annotations

import sqlite3
from pathlib import Path

from src.infra.settings import get_user_setting_candidates
from src.repositories import config_presets


def _db(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    schema = Path(__file__).resolve().parents[2] / "resources" / "schema.sql"
    conn.executescript(schema.read_text())
    conn.execute("INSERT INTO users (id, identifier, password_hash) VALUES ('user-1', 'u', 'h')")
    monkeypatch.setattr(config_presets, "get_connection", lambda: conn)
    get_user_setting_candidates.cache_clear()
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


def test_activating_specific_config_disables_rotation(monkeypatch):
    _db(monkeypatch)
    first = config_presets.save({"name": "first"}, "user-1")
    second = config_presets.save({"name": "second"}, "user-1")
    config_presets.save_rotation_config("user-1", True, [first, second])

    assert config_presets.set_active(second, "user-1")

    assert config_presets.get_rotation_config("user-1")["enabled"] == 0
    assert get_user_setting_candidates("user-1")[0].preset_name == "second"
