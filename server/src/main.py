from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.infra.logging import setup_logging
from src.infra.settings import get_settings
from src.infra.sqlite import init_db
from src.routes import dev, health
from src.routes.notes import router as notes_router
from src.routes.retrieval import router as retrieval_router
from src.routes.auth import router as auth_router
from src.routes.config import router as config_router
from src.services.rag.rag_service import get_rag_service


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Resume durable ingest jobs when the API process starts."""
    await get_rag_service().resume_pending_jobs()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings)
    init_db()

    # Initialize event bus and register listeners
    from src.infra.events import get_event_bus
    from src.services.notification import get_notification_service
    from src.services.rag.private.listener.listener import register_rag_listeners
    
    get_event_bus()
    get_notification_service()
    register_rag_listeners()

    app = FastAPI(title="UnmessIt.AI Server", lifespan=lifespan)
    # ponytail: local app, open CORS keeps Vite/dev clients simple.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(notes_router)
    app.include_router(retrieval_router)
    app.include_router(auth_router)
    app.include_router(config_router)
    app.include_router(dev.router)
    return app


app = create_app()
