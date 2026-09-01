import asyncio
import logging
import tempfile

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from src.exceptions.chunking_service import PdfParsingError
from src.services.ChunkingService.schemas import ParsedDocument, Section

logger = logging.getLogger(__name__)

# Docling gives a text block one of these labels when it's a heading, not
# normal body text. This is how we find where one section ends and the
# next one starts.
HEADING_LABELS = {"title", "section_header"}


class DoclingParser:
    """Parses PDF bytes and gives back the full text plus a list of
    sections (heading + body text)."""

    def __init__(self, max_pages: int, max_file_size_mb: int):
        pipeline_options = PdfPipelineOptions(
            do_table_structure=False,
            do_ocr=False,
            enable_remote_services=False,
        )
        self._converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
        )
        self._max_pages = max_pages
        self._max_file_size_bytes = max_file_size_mb * 1024 * 1024
        # One DoclingParser (and one DocumentConverter) is shared by every
        # request in the app so it does not have to reload its models on
        # each call. That also means two concurrent PDF parses would call
        # convert() on the same converter from two different threads at
        # once. This lock forces parses to happen one at a time, since
        # there is no guarantee Docling's converter is safe to use from
        # more than one thread at the same time.
        self._parse_lock = asyncio.Lock()

    async def parse(self, pdf_bytes: bytes) -> ParsedDocument:
        # Docling's parsing uses the CPU a lot and blocks while running, so
        # we run it in a separate thread here. Otherwise it would freeze
        # the whole async event loop while it works.
        async with self._parse_lock:
            return await asyncio.to_thread(self._parse_sync, pdf_bytes)

    def _parse_sync(self, pdf_bytes: bytes) -> ParsedDocument:
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp_file:
            tmp_file.write(pdf_bytes)
            tmp_file.flush()

            try:
                result = self._converter.convert(
                    tmp_file.name,
                    max_num_pages=self._max_pages,
                    max_file_size=self._max_file_size_bytes,
                )
            except Exception as e:
                logger.exception("Failed to parse PDF with Docling")
                raise PdfParsingError(f"Failed to parse PDF: {e}") from e

            document = result.document
            return ParsedDocument(
                raw_text=document.export_to_text(),
                sections=self._extract_sections(document),
            )

    def _extract_sections(self, document) -> list[Section]:
        """Goes through the parsed elements one by one, and starts a new
        section every time it sees a heading. Any text before the first
        heading is put under "Introduction"."""
        sections: list[Section] = []
        current_title = "Introduction"
        current_paragraphs: list[str] = []

        def flush_current_section() -> None:
            content = "\n\n".join(current_paragraphs).strip()
            if content:
                sections.append(Section(title=current_title, content=content))

        for element in document.texts:
            text = getattr(element, "text", None)
            if not text:
                continue

            if getattr(element, "label", None) in HEADING_LABELS:
                flush_current_section()
                current_title = text.strip()
                current_paragraphs = []
            else:
                current_paragraphs.append(text)

        flush_current_section()
        return sections
