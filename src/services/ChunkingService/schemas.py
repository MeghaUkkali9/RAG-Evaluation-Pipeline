from pydantic import BaseModel


class Section(BaseModel):
    """One heading plus the paragraphs under it, found by the parser."""

    title: str
    content: str


class ParsedDocument(BaseModel):
    """What DocumentParser.parse() gives back: the full text and its sections."""

    raw_text: str
    sections: list[Section]


class Chunk(BaseModel):
    chunk_index: int
    section_title: str
    content: str
