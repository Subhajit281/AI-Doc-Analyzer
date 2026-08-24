from dataclasses import dataclass
from typing import List

from app.sections.extractor import DocumentSection


@dataclass
class DocumentChunk:
    chunk_id: int
    text: str
    section: str
    page: int | None
    content_type: str

    parent_section: str | None = None
    section_path: str | None = None


class DocumentChunker:

    def __init__(
        self,
        chunk_size: int = 500,
        overlap: int = 50
    ):

        if overlap >= chunk_size:
            raise ValueError(
                "overlap must be smaller than chunk_size"
            )

        self.chunk_size = chunk_size
        self.overlap = overlap

    # =====================================================
    # Main
    # =====================================================

    def chunk(
        self,
        sections: List[DocumentSection]
    ) -> List[DocumentChunk]:

        chunks = []
        chunk_id = 0

        # Flatten hierarchy while preserving path
        flat_sections = self._flatten_sections(
            sections
        )

        for section in flat_sections:

            units = self._extract_units(
                section
            )

            if not units:
                continue

            current_units = []
            current_size = 0

            for unit in units:

                unit_words = unit.split()
                unit_size = len(unit_words)

                # -----------------------------------------
                # Oversized unit
                # -----------------------------------------

                if unit_size > self.chunk_size:

                    if current_units:

                        chunk_text = self._build_text(
                            section,
                            current_units
                        )

                        chunks.append(
                            self._create_chunk(
                                chunk_id,
                                chunk_text,
                                section
                            )
                        )

                        chunk_id += 1

                        current_units = []
                        current_size = 0

                    sub_chunks = self._split_large_unit(
                        unit_words
                    )

                    for sub_chunk in sub_chunks:

                        chunk_text = self._build_text(
                            section,
                            [sub_chunk]
                        )

                        chunks.append(
                            self._create_chunk(
                                chunk_id,
                                chunk_text,
                                section
                            )
                        )

                        chunk_id += 1

                    continue

                # -----------------------------------------
                # Add unit
                # -----------------------------------------

                if (
                    current_size + unit_size
                    <= self.chunk_size
                ):

                    current_units.append(unit)

                    current_size += unit_size

                else:

                    chunk_text = self._build_text(
                        section,
                        current_units
                    )

                    chunks.append(
                        self._create_chunk(
                            chunk_id,
                            chunk_text,
                            section
                        )
                    )

                    chunk_id += 1

                    overlap_units = (
                        self._get_overlap_units(
                            current_units
                        )
                    )

                    current_units = (
                        overlap_units + [unit]
                    )

                    current_size = sum(
                        len(x.split())
                        for x in current_units
                    )

            # -----------------------------------------
            # Final chunk
            # -----------------------------------------

            if current_units:

                chunk_text = self._build_text(
                    section,
                    current_units
                )

                chunks.append(
                    self._create_chunk(
                        chunk_id,
                        chunk_text,
                        section
                    )
                )

                chunk_id += 1

        return chunks

    # =====================================================
    # Flatten hierarchy
    # =====================================================

    def _flatten_sections(
        self,
        sections: List[DocumentSection]
    ) -> List[DocumentSection]:

        result = []

        def visit(
            section: DocumentSection
        ):

            result.append(section)

            for child in section.children:
                visit(child)

        for section in sections:
            visit(section)

        return result

    # =====================================================
    # Extract units
    # =====================================================

    def _extract_units(
        self,
        section: DocumentSection
    ) -> List[str]:

        units = []

        for item in section.items:

            if not item.text:
                continue

            text = item.text.strip()

            if text:
                units.append(text)

        return units

    # =====================================================
    # Build text
    # =====================================================

    def _build_text(
        self,
        section: DocumentSection,
        units: List[str]
    ) -> str:

        content = "\n".join(units)

        section_path = self._section_path(
            section
        )

        return (
            f"Section Path: {section_path}\n\n"
            f"{content}"
        )

    # =====================================================
    # Section path
    # =====================================================

    def _section_path(
        self,
        section: DocumentSection
    ) -> str:

        path = []

        current = section

        while current is not None:

            path.append(
                current.title
            )

            current = current.parent

        path.reverse()

        return " > ".join(path)

    # =====================================================
    # Create chunk
    # =====================================================

    def _create_chunk(
        self,
        chunk_id: int,
        text: str,
        section: DocumentSection
    ) -> DocumentChunk:

        parent_section = None

        if section.parent is not None:
            parent_section = (
                section.parent.title
            )

        return DocumentChunk(
            chunk_id=chunk_id,
            text=text,
            section=section.title,
            page=section.page,
            content_type="section",
            parent_section=parent_section,
            section_path=self._section_path(
                section
            )
        )

    # =====================================================
    # Split oversized unit
    # =====================================================

    def _split_large_unit(
        self,
        words: List[str]
    ) -> List[str]:

        result = []

        start = 0

        while start < len(words):

            end = min(
                start + self.chunk_size,
                len(words)
            )

            result.append(
                " ".join(
                    words[start:end]
                )
            )

            if end >= len(words):
                break

            start = end - self.overlap

        return result

    # =====================================================
    # Overlap
    # =====================================================

    def _get_overlap_units(
        self,
        units: List[str]
    ) -> List[str]:

        if self.overlap <= 0:
            return []

        selected = []
        count = 0

        for unit in reversed(units):

            unit_size = len(
                unit.split()
            )

            if (
                count + unit_size
                > self.overlap
            ):
                break

            selected.insert(
                0,
                unit
            )

            count += unit_size

        return selected