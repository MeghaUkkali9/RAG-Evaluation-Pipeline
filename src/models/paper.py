from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(primary_key=True)
    arxiv_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    title: Mapped[str] = mapped_column(Text)
    authors: Mapped[list[str]] = mapped_column(JSON)
    abstract: Mapped[str] = mapped_column(Text)
    categories: Mapped[list[str]] = mapped_column(JSON)
    pdf_url: Mapped[str] = mapped_column(Text)
    published_date: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_text: Mapped[str] = mapped_column(Text)
