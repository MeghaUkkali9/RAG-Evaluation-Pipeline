from enum import StrEnum

from src.services.ChunkingService.section_chunker import SectionAwareChunker

# Abstract and Conclusion carry outsized retrieval value relative to their
# length, so the "academic" preset never lets them get merged away just
# for being short.
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
        # Isolates whether overlap adds anything on top of section-based
        # cuts. Section boundaries are already real semantic edges, unlike
        # the arbitrary cut points overlap is normally meant to protect
        # against - if this scores the same as SECTION_AWARE_400, the
        # overlap can be dropped for a smaller index at no retrieval cost.
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
