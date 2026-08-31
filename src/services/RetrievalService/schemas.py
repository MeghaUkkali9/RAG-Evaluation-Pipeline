from pydantic import BaseModel


class SearchHit(BaseModel):
    arxiv_id: str
    chunk_index: int
    section_title: str
    content: str
    score: float
