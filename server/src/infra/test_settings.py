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

    assert settings.llm_provider == "ollama"
    assert settings.llm_model == "llama3.2:latest"
    assert settings.llm_base_url is None
    assert settings.llm_api_key == ""
    assert settings.embedding_provider == "ollama"
    assert settings.embedding_model == "nomic-embed-text"
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
