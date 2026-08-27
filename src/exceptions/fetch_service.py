from src.exceptions.base import AppError


class FetchServiceError(AppError):
    """Base class for all FetchService errors (e.g. arXiv/network failures)."""

    code = "fetch_service_error"
    status_code = 502


class ArxivEntryNotFoundError(FetchServiceError):
    code = "arxiv_entry_not_found"
    status_code = 404

    def __init__(self, arxiv_id: str):
        super().__init__(f"No arXiv entry found for id '{arxiv_id}'")
        self.arxiv_id = arxiv_id
