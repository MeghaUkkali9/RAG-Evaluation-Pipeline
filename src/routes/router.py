from fastapi import APIRouter, Depends, Request, status

from src.dependencies import get_fetch_service_client
from src.services.FetchService.client import FetchServiceClient
from src.services.FetchService.schemas import PaperMetadata

router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(request: Request):
    return {"status": "API is running"}


@router.get("/papers/{arxiv_id}/metadata", response_model=PaperMetadata)
async def get_paper_metadata(
    arxiv_id: str,
    fetch_srevice_client: FetchServiceClient = Depends(get_fetch_service_client)):
    metadata = await fetch_srevice_client.fetch_paper_metadata(arxiv_id)
    return metadata

@router.get("/papers/{arxiv_id}/fetch", response_model=PaperMetadata)
async def fetch_and_store_paper_metadata(
    arxiv_id: str,
    fetch_service_client: FetchServiceClient = Depends(get_fetch_service_client)):
    metadata = await fetch_service_client.fetch_and_store_paper_metadata(arxiv_id)
    return metadata
