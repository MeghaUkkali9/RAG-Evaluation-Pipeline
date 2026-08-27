from fastapi import APIRouter, Depends, Request, status

from src.dependencies import get_fetch_service_client
from src.services.FetchService.client import FetchServiceClient
from src.services.FetchService.schemas import PaperMetadata

router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(request: Request):
    """
    Health check endpoint to verify if the API is running.
    """
    return {"status": "API is running"}


@router.get("/papers/{arxiv_id}", response_model=PaperMetadata, status_code=status.HTTP_200_OK)
async def get_paper_metadata(
    arxiv_id: str,
    fetch_service_client: FetchServiceClient = Depends(get_fetch_service_client),
) -> PaperMetadata:
    """
    Fetch arXiv metadata for a paper by its arXiv id.
    """
    return await fetch_service_client.fetch_paper_metadata(arxiv_id)
