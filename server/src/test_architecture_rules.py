from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _active_py_files():
    return [
        path for path in ROOT.rglob("*.py")
        if "__pycache__" not in path.parts and path.name != "test_architecture_rules.py"
    ]


def test_no_di_container_or_old_engine_imports():
    banned = (
        "kink",
        "di[",
        "services.ingest_engine",
        "services.retrieval_engine",
        "RetrievalServiceContract",
        "Ingestor",
        "memory_items",
        "memory_subject",
        "atoms",
        "episodes",
    )
    offenders = []
    for path in _active_py_files():
        text = path.read_text()
        if any(item in text for item in banned):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_repositories_are_plain_function_modules():
    offenders = []
    for path in (ROOT / "repositories").glob("*.py"):
        if path.name == "__init__.py":
            continue
        if "\nclass " in path.read_text():
            offenders.append(path.name)
    assert offenders == []


def test_public_rag_service_getter_exists():
    text = (ROOT / "services/rag/rag_service.py").read_text()
    assert "class RagService(Protocol)" in text
    assert "def get_rag_service()" in text


def test_routes_keep_public_urls():
    assert 'APIRouter(prefix="/notes"' in (ROOT / "routes/notes.py").read_text()
    assert 'APIRouter(prefix="/api/retrieval"' in (ROOT / "routes/retrieval.py").read_text()
    assert 'APIRouter(prefix="/dev"' in (ROOT / "routes/dev.py").read_text()
