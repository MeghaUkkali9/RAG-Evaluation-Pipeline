from enum import StrEnum

from src.services.ChunkingService.section_chunker import SectionAwareChunker

# Abstract and Conclusion are short but still important, so the "academic"
# preset never merges them away with other small sections just because
# they are short.
ACADEMIC_PROTECTED_TITLES = frozenset({"abstract", "conclusion", "conclusions", "summary"})


class ChunkingStrategyName(StrEnum):
    SECTION_AWARE_400 = "section_aware_400"
    SECTION_AWARE_400_NO_OVERLAP = "section_aware_400_no_overlap"
    SECTION_AWARE_700 = "section_aware_700"
    SECTION_AWARE_ACADEMIC = "section_aware_academic"


def build_chunking_strategy(name: ChunkingStrategyName) -> SectionAwareChunker:
    if name == ChunkingStrategyName.SECTION_AWARE_400:
        return SectionAwareChunker(min_section_words=100, max_section_words=400, overlap_words=50)

    if name == ChunkingStrategyName.SECTION_AWARE_400_NO_OVERLAP:
        # This checks if overlap even helps on top of section-based cuts.
        # A section boundary is already a real break in the text, not an
        # arbitrary cut point like overlap is normally there to protect.
        # If this scores the same as SECTION_AWARE_400, we can drop the
        # overlap and get a smaller index for free.
        return SectionAwareChunker(min_section_words=100, max_section_words=400, overlap_words=0)

    if name == ChunkingStrategyName.SECTION_AWARE_700:
        return SectionAwareChunker(min_section_words=100, max_section_words=700, overlap_words=100)

    if name == ChunkingStrategyName.SECTION_AWARE_ACADEMIC:
        return SectionAwareChunker(
            min_section_words=100,
            max_section_words=450,
            overlap_words=100,
            include_abstract=True,
            protected_section_titles=ACADEMIC_PROTECTED_TITLES,
        )

    raise ValueError(f"Unknown chunking strategy: {name}")
