from fastapi import APIRouter, Depends, Request, status

from src.dependencies import get_fetch_service_client, get_ingestion_service
from src.services.FetchService.client import FetchServiceClient
from src.services.FetchService.schemas import PaperMetadata
from src.services.ingestion import IngestionService

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

@router.post("/papers/{arxiv_id}/ingest", response_model=PaperMetadata)
async def ingest_paper(
    arxiv_id: str,
    ingestion_service: IngestionService = Depends(get_ingestion_service)):
    return await ingestion_service.ingest_paper(arxiv_id)
