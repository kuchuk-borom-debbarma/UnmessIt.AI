import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.infra.settings import Settings
from src.infra.logging import setup_logging
from src.infra.sqlite import init_db
from src.services.ingest_engine.adapters.inbound.listener import start_ingest_listener
import src.routes.health as health
import src.routes.ingest as ingest
import src.routes.dev as dev
import src.routes.retrieval as retrieval

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the ingest listener background task
    listener_task = asyncio.create_task(start_ingest_listener())
    yield
    # Cleanup task on shutdown
    listener_task.cancel()

def create_app() -> FastAPI:
    settings = Settings()
    setup_logging(settings)
    
    # Initialize the SQLite database tables
    init_db()
    
    # Setup Dependency Injection
    from src.infra.di.bootstrap import setup_di
    setup_di(settings)

    app = FastAPI(title="UnmessIt.AI Server", lifespan=lifespan)
    
    # ponytail: enable CORS for local development to connect Vite frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.settings = settings
    app.include_router(health.router)
    app.include_router(ingest.router)
    app.include_router(dev.router)
    app.include_router(retrieval.router)
    return app


app = create_app()
