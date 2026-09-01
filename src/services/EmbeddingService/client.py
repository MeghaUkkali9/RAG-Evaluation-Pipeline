from typing import Protocol

from openai import AsyncOpenAI

# Dimension and price both depend on which model we use, so we keep them
# here together instead of as separate settings somewhere else. This way
# they can't get out of sync with the model actually being used.
EMBEDDING_MODEL_SPECS = {
    "text-embedding-3-small": {
        "dimensions": 1536, 
        "price_per_million_tokens_usd": 0.02
    },
}

# sending texts in batches means we don't make one API call per chunk
# when we index a whole corpus - much cheaper and faster.
MAX_BATCH_SIZE = 100


class EmbeddingClient(Protocol):
    async def embed(self, texts: list[str]) -> tuple[list[list[float]], int]:
        """Returns (embeddings, total_tokens_used)."""
        ...


class OpenAIEmbeddingClient:
    def __init__(self, client: AsyncOpenAI, model: str):
        self._client = client
        self._model = model

    async def embed(self, texts: list[str]) -> tuple[list[list[float]], int]:
        all_embeddings: list[list[float]] = []
        total_tokens = 0

        for start in range(0, len(texts), MAX_BATCH_SIZE):
            batch = texts[start : start + MAX_BATCH_SIZE]
            
            response = await self._client.embeddings.create(model=self._model, input=batch)
            
            for item in response.data:
                all_embeddings.append(item.embedding)
            
            total_tokens += response.usage.total_tokens

        return all_embeddings, total_tokens
