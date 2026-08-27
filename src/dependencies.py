from fastapi import Request

from src.services.FetchService.client import FetchServiceClient


async def get_fetch_service_client(request: Request) -> FetchServiceClient:
    """
    Returns the app-lifetime FetchServiceClient built in main.py's lifespan.
    """

    return request.app.state.fetch_service_client
