from fastapi import Depends, Request
from sqlalchemy.orm import Session

from src.database import get_db_session
from src.repositories.PaperRepository import PaperRepository
from src.services.FetchService.client import FetchServiceClient
from src.services.ingestion import IngestionService


async def get_fetch_service_client(request: Request) -> FetchServiceClient:
    return request.app.state.fetch_service_client


def get_ingestion_service(
    request: Request,
    session: Session = Depends(get_db_session),
) -> IngestionService:
    return IngestionService(
        fetch_service_client=request.app.state.fetch_service_client,
        chunking_service_client=request.app.state.chunking_service_client,
        indexing_service_client=request.app.state.indexing_service_client,
        paper_repository=PaperRepository(session),
    )
