from src.config import Settings
from src.services.ChunkingService.client import ChunkingServiceClient
from src.services.ChunkingService.docling_parser import DoclingParser
from src.services.ChunkingService.section_chunker import SectionAwareChunker


def create_chunking_service_client(settings: Settings) -> ChunkingServiceClient:
    parser = DoclingParser(
        max_pages=settings.pdf_max_pages,
        max_file_size_mb=settings.pdf_max_file_size_mb,
    )
    chunker = SectionAwareChunker(
        min_section_words=settings.chunk_min_words,
        max_section_words=settings.chunk_max_words,
        overlap_words=settings.chunk_overlap_words,
    )

    return ChunkingServiceClient(parser=parser, chunker=chunker)
