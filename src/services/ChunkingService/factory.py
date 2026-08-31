from src.config import Settings
from src.services.ChunkingService.client import ChunkingServiceClient
from src.services.ChunkingService.docling_parser import DoclingParser
from src.services.ChunkingService.strategies import ChunkingStrategyName, build_chunking_strategy


def create_chunking_service_client(settings: Settings) -> ChunkingServiceClient:
    parser = DoclingParser(
        max_pages=settings.pdf_max_pages,
        max_file_size_mb=settings.pdf_max_file_size_mb,
    )
    chunker = build_chunking_strategy(ChunkingStrategyName(settings.chunking_strategy))

    return ChunkingServiceClient(parser=parser, chunker=chunker)
