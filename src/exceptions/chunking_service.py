from src.exceptions.base import AppError


class ChunkingServiceError(AppError):
    code = "chunking_service_error"
    status_code = 502


class PdfParsingError(ChunkingServiceError):
    code = "pdf_parsing_error"
