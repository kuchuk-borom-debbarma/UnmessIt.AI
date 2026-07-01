from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.infra.logging import setup_logging
from src.infra.settings import get_settings
from src.infra.sqlite import init_db
from src.routes import advanced, dev, directories, health, ingest, tags
from src.routes.notes import router as notes_router
from src.routes.retrieval import router as retrieval_router
from src.routes.auth import router as auth_router
from src.routes.config import router as config_router
from src.services.rag.rag_service import get_rag_service


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Resume durable ingest jobs when the API process starts."""
    from src.services.rag.private.durability.events import register_ingest_job_sse_bridge
    register_ingest_job_sse_bridge()
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
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    from fastapi import APIRouter
    api_router = APIRouter(prefix="/api/v1")
    
    api_router.include_router(health.router)
    api_router.include_router(ingest.router)
    api_router.include_router(notes_router)
    api_router.include_router(directories.router)
    api_router.include_router(tags.router)
    api_router.include_router(retrieval_router)
    api_router.include_router(auth_router)
    api_router.include_router(config_router)
    api_router.include_router(advanced.router)
    if settings.enable_dev_routes:
        api_router.include_router(dev.router)
        
    app.include_router(api_router)
        
    from fastapi import Request
    from fastapi.responses import JSONResponse
    from src.infra.settings import NoActivePresetError
    
    @app.exception_handler(NoActivePresetError)
    async def no_active_preset_handler(request: Request, exc: NoActivePresetError):
        return JSONResponse(
            status_code=428,
            content={"status": "error", "code": "no_active_preset", "message": str(exc)},
        )
        
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    
    # Run the server on the default port 2317
    uvicorn.run("src.main:app", host="127.0.0.1", port=2317, reload=True)
