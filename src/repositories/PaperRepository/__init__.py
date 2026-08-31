from sqlalchemy.orm import Session

from src.models.paper import Paper
from src.services.ChunkingService.schemas import ParsedDocument
from src.services.FetchService.schemas import PaperMetadata


class PaperRepository:
    def __init__(self, session: Session):
        self._session = session

    def save_paper(self, metadata: PaperMetadata, parsed: ParsedDocument) -> Paper:
        paper = Paper(
            arxiv_id=metadata.arxiv_id,
            title=metadata.title,
            authors=metadata.authors,
            abstract=metadata.abstract,
            categories=metadata.categories,
            pdf_url=metadata.pdf_url,
            published_date=metadata.published_date,
            raw_text=parsed.raw_text,
            sections=[section.model_dump() for section in parsed.sections],
        )

        self._session.add(paper)
        self._session.commit()
        self._session.refresh(paper)
        return paper
