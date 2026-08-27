from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.exceptions import register_exception_handlers
from src.routes import router
from src.services.FetchService.factory import create_fetch_service_client


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.fetch_service_client = create_fetch_service_client(settings)

    yield

    await app.state.fetch_service_client.aclose()


app = FastAPI(
        title="RAG Pipeline API",
        description="This is a RAG Pipeline API built using FastAPI.",
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

app.include_router(router, prefix="/api/v1", tags=["RAG Pipeline"])
