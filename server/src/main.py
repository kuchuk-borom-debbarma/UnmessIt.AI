from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.infra.logging import setup_logging
from src.infra.settings import get_settings
from src.infra.sqlite import init_db
from src.routes import dev, health, ingest, retrieval
from src.services.rag.rag_service import get_rag_service


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Resume durable ingest jobs when the API process starts."""
    get_rag_service().resume_pending_jobs()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings)
    init_db()

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
    app.include_router(ingest.router)
    app.include_router(dev.router)
    app.include_router(retrieval.router)
    return app


app = create_app()
