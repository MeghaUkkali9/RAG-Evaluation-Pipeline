from openai import AsyncOpenAI

from src.config import Settings
from src.services.EmbeddingService.client import OpenAIEmbeddingClient


def create_embedding_client(settings: Settings) -> OpenAIEmbeddingClient:
    
    return OpenAIEmbeddingClient(
        client=AsyncOpenAI(),
        model=settings.embedding_model
    )
