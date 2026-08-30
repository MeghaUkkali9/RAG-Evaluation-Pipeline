from pydantic import BaseModel


class Section(BaseModel):
    """One heading + the paragraphs under it, as detected by the parser."""

    title: str
    content: str


class ParsedDocument(BaseModel):
    """What DocumentParser.parse() returns: the full text plus its sections."""

    raw_text: str
    sections: list[Section]


class Chunk(BaseModel):
    chunk_index: int
    section_title: str
    content: str
