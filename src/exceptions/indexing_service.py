from src.exceptions.base import AppError


class IndexingServiceError(AppError):
    code = "indexing_service_error"
    status_code = 502
