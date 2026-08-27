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


@router.get("/papers/{arxiv_id}/metadata", response_model=PaperMetadata)
async def get_paper_metadata(
    arxiv_id: str, 
    fetch_srevice_client: FetchServiceClient = Depends(get_fetch_service_client)):
    """
    Fetches metadata for a paper given its arXiv ID.
    """
    metadata = await fetch_srevice_client.fetch_paper_metadata(arxiv_id)
    return metadata
