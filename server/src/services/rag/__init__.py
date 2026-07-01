from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.rag.rag_service import RagService, get_rag_service


def __getattr__(name: str):
    if name in {"RagService", "get_rag_service"}:
        from src.services.rag.rag_service import RagService, get_rag_service

        return {"RagService": RagService, "get_rag_service": get_rag_service}[name]
    raise AttributeError(name)

__all__ = ["RagService", "get_rag_service"]
