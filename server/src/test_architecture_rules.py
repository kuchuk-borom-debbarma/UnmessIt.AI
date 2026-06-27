from pathlib import Path


ROOT = Path(__file__).resolve().parent


def _py_files(path: str):
    return (ROOT / path).rglob("*.py")


def test_routes_do_not_import_sqlite():
    offenders = [
        path for path in _py_files("routes")
        if "get_db_connection" in path.read_text()
    ]
    assert offenders == []


def test_listener_uses_di_not_concrete_adapters():
    listener = (ROOT / "services/ingest_engine/adapters/inbound/listener.py").read_text()
    assert "SqliteIngestRepository" not in listener
    assert "ChromaVectorStoreImpl" not in listener
    assert "factory" not in listener
    assert "di[Ingestor]" in listener
    assert "di[EventBus]" in listener


def test_ingest_engine_uses_hex_layout():
    ingest = ROOT / "services/ingest_engine"
    assert (ingest / "ports/inbound/ingestor.py").exists()
    assert (ingest / "adapters/inbound/listener.py").exists()
    assert (ingest / "domain/seai/ingestor.py").exists()
    assert not (ingest / "private").exists()
    assert not (ingest / "public").exists()


def test_active_code_has_no_legacy_iteration_imports():
    banned = (
        "deterministic_ingestor",
        "third_iteration",
        "fourth_iteration",
        "fifth_iteration",
        "master_ingest_service",
        "MasterRetrievalService",
        "services.retrieval_engine.adapters",
        "services.ingest_engine.private.repositories",
        "services.ingest_engine.private.pipes",
        "services.ingest_engine.private",
        "services.ingest_engine.public",
    )
    offenders = []
    for path in _py_files("."):
        if path.name.startswith("test_"):
            continue
        text = path.read_text()
        if any(item in text for item in banned):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_services_do_not_import_langchain_directly():
    banned = (
        "langchain_core",
        "langchain_openai",
        "langchain_ollama",
        "get_chat_llm",
        "JsonOutputParser",
        "SystemMessage",
        "HumanMessage",
        "src.infra.langchain",
    )
    offenders = []
    for base in ("services", "routes"):
        for path in _py_files(base):
            if path.name.startswith("test_"):
                continue
            text = path.read_text()
            if any(item in text for item in banned):
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_event_bus_is_resolved_through_di():
    offenders = []
    for base in ("services", "routes"):
        for path in _py_files(base):
            if "event_bus.instance" in path.read_text():
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_retrieval_llm_uses_env_token_budget():
    bootstrap = (ROOT / "infra/di/bootstrap.py").read_text()
    assert "LLMJsonClient(max_tokens=2048)" not in bootstrap
