from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes import router

app = FastAPI(
        title="RAG Pipeline API",
        description="This is a RAG Pipeline API built using FastAPI.",
        version="1.0.0",
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1", tags=["RAG Pipeline"])