from src.services.ChunkingService.schemas import Chunk, ParsedDocument, Section


class SectionAwareChunker:
    """Turns a parsed paper into retrieval-sized chunks, splitting along
    section boundaries instead of cutting text at an arbitrary word count.

    Rules:
    - A section that's a reasonable size becomes one chunk as-is.
    - Small sections (e.g. a two-line "Limitations" section) are merged
      with the small sections next to them, so we don't index near-empty
      chunks - unless their title is in `protected_section_titles`, since
      some short sections (Abstract, Conclusion) are high-value on their
      own and shouldn't get diluted by merging.
    - Oversized sections (e.g. a long "Experiments" section) are split
      further with a sliding word window, but the window never crosses
      into the next section - that would defeat the point of chunking
      by section in the first place.
    - Every chunk starts with the paper title (and, if `include_abstract`
      is set, the abstract) plus its section title, so a chunk still
      makes sense to a retriever even without its neighbors.
    """

    def __init__(
        self,
        min_section_words: int,
        max_section_words: int,
        overlap_words: int,
        include_abstract: bool = False,
        protected_section_titles: frozenset[str] = frozenset(),
    ):
        if overlap_words >= max_section_words:
            raise ValueError("overlap_words must be smaller than max_section_words")

        self._min_words = min_section_words
        self._max_words = max_section_words
        self._overlap_words = overlap_words
        self._include_abstract = include_abstract
        self._protected_titles = {title.lower() for title in protected_section_titles}

    def chunk(self, paper_title: str, abstract: str, parsed: ParsedDocument) -> list[Chunk]:
        sections = [s for s in parsed.sections if s.content.strip()]

        if not sections:
            # Parser found no headings (e.g. a scanned or unusually
            # formatted PDF) - fall back to chunking the raw text as one
            # big "Document" section.
            fallback = Section(title="Document", content=parsed.raw_text)
            return self._number(self._split_section(paper_title, abstract, fallback))

        chunks: list[Chunk] = []
        small_sections: list[Section] = []

        def flush_small_sections() -> None:
            if not small_sections:
                return
            merged = self._merge_sections(small_sections)
            chunks.extend(self._split_section(paper_title, abstract, merged))
            small_sections.clear()

        for section in sections:
            is_small = len(section.content.split()) < self._min_words
            is_protected = section.title.lower() in self._protected_titles

            if is_small and not is_protected:
                small_sections.append(section)
                continue

            flush_small_sections()
            chunks.extend(self._split_section(paper_title, abstract, section))

        flush_small_sections()
        return self._number(chunks)

    def _merge_sections(self, sections: list[Section]) -> Section:
        combined_title = " + ".join(s.title for s in sections)
        combined_content = "\n\n".join(s.content for s in sections)
        return Section(title=combined_title, content=combined_content)

    def _split_section(self, paper_title: str, abstract: str, section: Section) -> list[Chunk]:
        """Turn one section into one or more chunks, sliding a word window
        over it only if it's bigger than max_section_words."""
        words = section.content.split()
        step = self._max_words - self._overlap_words

        windows = [
            " ".join(words[start : start + self._max_words])
            for start in range(0, len(words), step)
        ]

        return [self._make_chunk(paper_title, abstract, section.title, window) for window in windows]

    def _make_chunk(self, paper_title: str, abstract: str, section_title: str, content: str) -> Chunk:
        header = f"{paper_title}\n\n"
        if self._include_abstract and abstract:
            header += f"Abstract: {abstract}\n\n"
        header += f"Section: {section_title}\n\n"

        # chunk_index is filled in by _number() once the full list is known.
        return Chunk(chunk_index=-1, section_title=section_title, content=header + content)

    def _number(self, chunks: list[Chunk]) -> list[Chunk]:
        return [chunk.model_copy(update={"chunk_index": i}) for i, chunk in enumerate(chunks)]
