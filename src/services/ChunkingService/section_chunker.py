from src.services.ChunkingService.schemas import Chunk, ParsedDocument, Section


class SectionAwareChunker:
    """Turns a parsed paper into chunks that are good for retrieval by
    cutting section boundaries.
    Rules:
    - A section with a normal size becomes one chunk as it is.
    - Small sections (like a two-line section) get merged
      with the small sections next to them so I don't index empty or nearly empty
      chunks unless the title is in protected_section_titles because
      short sections such as Abstract, Conclusion are important on their own
      and should not get merged into something else.
    - Sections that are too big get split with a sliding word window 
      but the window never goes into the next section.
    - Every chunk starts with the paper title(and the abstract too if
      include_abstract is on) plus its section title.
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

        protected_titles = set()
        
        for title in protected_section_titles:
            protected_titles.add(title.lower())
            
        self._protected_titles = protected_titles

    def chunk(self, paper_title: str, abstract: str, parsed: ParsedDocument) -> list[Chunk]:
        sections = []
        for section in parsed.sections:
            if section.content.strip():
                sections.append(section)

        if not sections:
            # Parser did not find any headings(for example a scanned PDF,
            # or one with strange formatting) just treat the whole
            # text as one big "Document" section instead of failing.
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
        titles = []
        contents = []
        for section in sections:
            titles.append(section.title)
            contents.append(section.content)

        combined_title = " + ".join(titles)
        combined_content = "\n\n".join(contents)
        return Section(title=combined_title, content=combined_content)

    def _split_section(self, paper_title: str, abstract: str, section: Section) -> list[Chunk]:
        """Turns one section into one or more chunks. Only slides a word
        window over it if the section is bigger than max_section_words."""
        words = section.content.split()
        step = self._max_words - self._overlap_words

        windows = []
        for start in range(0, len(words), step):
            window_words = words[start : start + self._max_words]
            windows.append(" ".join(window_words))

        chunks = []
        for window in windows:
            chunks.append(self._make_chunk(paper_title, abstract, section.title, window))
        return chunks

    def _make_chunk(self, paper_title: str, abstract: str, section_title: str, content: str) -> Chunk:
        header = f"{paper_title}\n\n"
        if self._include_abstract and abstract:
            header += f"Abstract: {abstract}\n\n"
        header += f"Section: {section_title}\n\n"

        return Chunk(chunk_index=-1, section_title=section_title, content=header + content)

    def _number(self, chunks: list[Chunk]) -> list[Chunk]:
        numbered_chunks = []
        for i, chunk in enumerate(chunks):
            numbered_chunks.append(chunk.model_copy(update={"chunk_index": i}))
        return numbered_chunks
