from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.database import init_db
from src.exceptions import register_exception_handlers
from src.models import experiment_run, paper  # noqa: F401 (registers tables on Base.metadata)
from src.routes import router
from src.services.ChunkingService.factory import create_chunking_service_client
from src.services.FetchService.factory import create_fetch_service_client
from src.services.IndexingService.factory import create_indexing_service_client


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    init_db()

    app.state.fetch_service_client = create_fetch_service_client(settings)
    app.state.chunking_service_client = create_chunking_service_client(settings)
    app.state.indexing_service_client = create_indexing_service_client(settings)
    await app.state.indexing_service_client.ensure_index()

    yield

    await app.state.fetch_service_client.aclose()
    await app.state.indexing_service_client.aclose()


app = FastAPI(
        title="RAG Evaluation Pipeline API",
        description="RAG Evaluation Pipeline API built using FastAPI.",
        version="1.0.0",
        lifespan=lifespan,
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(router, prefix="/api/v1", tags=["RAG Evaluation Pipeline"])
