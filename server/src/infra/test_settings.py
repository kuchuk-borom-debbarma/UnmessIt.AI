import json

from src.infra import chroma, langchain_json
from src.infra.progress import set_last_embedding_rotation_snapshot
from src.infra.settings import Settings


def test_ai_settings_ignore_legacy_environment_variables(monkeypatch):
    monkeypatch.setenv("INGEST_MODEL_PROVIDER", "openai")
    monkeypatch.setenv("INGEST_MODEL_NAME", "env-text-model")
    monkeypatch.setenv("INGEST_MODEL_BASE_URL", "https://env.example/v1")
    monkeypatch.setenv("INGEST_MODEL_API_KEY", "env-text-key")
    monkeypatch.setenv("EMBEDDING_MODEL_PROVIDER", "openai")
    monkeypatch.setenv("EMBEDDING_MODEL_NAME", "env-embedding-model")
    monkeypatch.setenv("EMBEDDING_MODEL_BASE_URL", "https://env.example/v1")
    monkeypatch.setenv("EMBEDDING_MODEL_API_KEY", "env-embedding-key")

    settings = Settings()

    assert settings.llm_provider == "openai"
    assert settings.llm_model == "gpt-4o"
    assert settings.llm_base_url is None
    assert settings.llm_api_key == ""
    assert settings.embedding_provider == "openai"
    assert settings.embedding_model == "text-embedding-3-small"
    assert settings.embedding_base_url is None
    assert settings.embedding_api_key == ""


def test_ai_settings_use_user_preset_values(monkeypatch):
    monkeypatch.setenv("INGEST_MODEL_PROVIDER", "ignored")
    preset = {
        "llm_provider": "openai",
        "llm_model": "preset-text-model",
        "llm_base_url": "https://preset.example/v1",
        "llm_api_key": "preset-text-key",
        "embedding_provider": "openai",
        "embedding_model": "preset-embedding-model",
        "embedding_base_url": "https://preset.example/v1",
        "embedding_api_key": "preset-embedding-key",
        "ingest_retry_backoff_seconds": "1,2,5",
    }

    settings = Settings(preset)

    assert settings.llm_provider == "openai"
    assert settings.llm_model == "preset-text-model"
    assert settings.llm_base_url == "https://preset.example/v1"
    assert settings.llm_api_key == "preset-text-key"
    assert settings.embedding_provider == "openai"
    assert settings.embedding_model == "preset-embedding-model"
    assert settings.embedding_base_url == "https://preset.example/v1"
    assert settings.embedding_api_key == "preset-embedding-key"
    assert settings.ingest_retry_backoff_seconds == [1, 2, 5]


def test_ai_settings_sanitize_retry_backoff_seconds():
    settings = Settings({"ingest_retry_backoff_seconds": "0, bad, 12, 99999"})

    assert settings.ingest_retry_backoff_seconds == [0, 12]


def test_ai_settings_rewrite_loopback_base_urls_in_docker(monkeypatch):
    monkeypatch.setenv("UNMESSIT_DOCKER", "1")
    preset = {
        "llm_base_url": "http://localhost:1234/v1",
        "embedding_base_url": "http://127.0.0.1:1234/v1",
    }

    settings = Settings(preset)

    assert settings.llm_base_url == "http://host.docker.internal:1234/v1"
    assert settings.embedding_base_url == "http://host.docker.internal:1234/v1"


def test_ai_settings_leave_external_base_urls_in_docker(monkeypatch):
    monkeypatch.setenv("UNMESSIT_DOCKER", "1")
    settings = Settings({"llm_base_url": "https://integrate.api.nvidia.com/v1"})

    assert settings.llm_base_url == "https://integrate.api.nvidia.com/v1"


async def test_llm_rotation_falls_through_to_next_candidate(monkeypatch):
    calls = []
    candidates = (
        Settings({"id": "bad", "name": "bad", "llm_model": "bad-model"}),
        Settings({"id": "good", "name": "good", "llm_model": "good-model"}),
    )

    class FakeResponse:
        content = '{"ok": true}'

    class FakeLLM:
        def __init__(self, model: str) -> None:
            self.model = model

        async def ainvoke(self, messages, **kwargs):
            calls.append(self.model)
            if self.model == "bad-model":
                raise RuntimeError("down")
            return FakeResponse()

    monkeypatch.setattr(langchain_json, "get_user_setting_candidates", lambda user_id: candidates)
    monkeypatch.setattr(langchain_json, "_get_chat_llm", lambda cache_key: FakeLLM(cache_key[2]))

    result = await langchain_json.JsonLLMClient().async_invoke_json("system", "human", "user-1")

    assert result == {"ok": True}
    assert calls == ["bad-model", "good-model"]


async def test_official_openai_preset_passes_prompt_cache_key(monkeypatch):
    calls = []
    candidates = (Settings({"id": "openai", "llm_model": "gpt-4o"}),)

    class FakeResponse:
        content = '{"ok": true}'

    class FakeLLM:
        async def ainvoke(self, messages, **kwargs):
            calls.append(kwargs)
            return FakeResponse()

    monkeypatch.setattr(langchain_json, "get_user_setting_candidates", lambda user_id: candidates)
    monkeypatch.setattr(langchain_json, "_get_chat_llm", lambda cache_key: FakeLLM())

    result = await langchain_json.JsonLLMClient().async_invoke_json("stable system", "human", "user-1")

    assert result == {"ok": True}
    assert calls[0]["prompt_cache_key"].startswith("openai:gpt-4o:api.openai.com:")


async def test_custom_openai_base_url_skips_prompt_cache_key(monkeypatch):
    calls = []
    candidates = (Settings({"id": "custom", "llm_base_url": "http://localhost:1234/v1"}),)

    class FakeResponse:
        content = '{"ok": true}'

    class FakeLLM:
        async def ainvoke(self, messages, **kwargs):
            calls.append(kwargs)
            return FakeResponse()

    monkeypatch.setattr(langchain_json, "get_user_setting_candidates", lambda user_id: candidates)
    monkeypatch.setattr(langchain_json, "_get_chat_llm", lambda cache_key: FakeLLM())

    result = await langchain_json.JsonLLMClient().async_invoke_json("stable system", "human", "user-1")

    assert result == {"ok": True}
    assert calls == [{}]


def test_chroma_upsert_writes_actual_embedding_rotation_snapshot(monkeypatch):
    updates = {}

    class FakeCollection:
        def upsert(self, ids, documents, metadatas):
            set_last_embedding_rotation_snapshot({"preset_id": "embed-good", "preset_name": "embed good"})

        def update(self, ids, metadatas):
            updates["ids"] = ids
            updates["metadatas"] = metadatas

    monkeypatch.setattr(chroma, "_user_collection", lambda user_id: FakeCollection())

    chroma.upsert(["vec-1"], ["text"], [{"object_type": "source_chunk"}], "user-1")

    assert updates["ids"] == ["vec-1"]
    assert json.loads(updates["metadatas"][0]["embedding_rotation_preset"])["preset_id"] == "embed-good"
