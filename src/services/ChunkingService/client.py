from typing import Protocol

from src.services.ChunkingService.schemas import Chunk, ParsedDocument


class DocumentParser(Protocol):
    async def parse(self, pdf_bytes: bytes) -> ParsedDocument: ...


class SectionChunker(Protocol):
    def chunk(self, paper_title: str, parsed: ParsedDocument) -> list[Chunk]: ...


class ChunkingServiceClient:
    def __init__(self, parser: DocumentParser, chunker: SectionChunker):
        self._parser = parser
        self._chunker = chunker

    async def parse(self, pdf_bytes: bytes) -> ParsedDocument:
        return await self._parser.parse(pdf_bytes)

    def chunk(self, paper_title: str, parsed: ParsedDocument) -> list[Chunk]:
        return self._chunker.chunk(paper_title, parsed)
