from pydantic import BaseModel, Field
from typing import Optional

class PaperMetadata(BaseModel):
    """
    Represents the metadata of paper.
    """
    arxiv_id: str = Field(..., description="The unique identifier of paper on arXiv.")
    title: str = Field(..., description="The title of the paper.")
    authors: list[str] = Field(..., description="List of authors of the paper.")
    abstract: str = Field(..., description="The abstract of the paper.")
    categories: list[str] = Field(..., description="List of categories the paper belongs to.")
    pdf_url: str = Field(..., description="URL to download the PDF of the paper.")
    published_date: str = Field(None, description="The date when the paper was published.")
    
class FetchedPaper(BaseModel):
    """
    Represents paper along with its metadata and PDF content.
    """
    metadata: PaperMetadata = Field(..., description="The metadata of the paper.")
    pdf_bytes: bytes = Field(..., description="The binary content of the paper's PDF.")