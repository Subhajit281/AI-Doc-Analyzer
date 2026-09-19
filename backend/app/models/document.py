from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class DocumentMetadata:
    filename: str
    file_type: str
    size_bytes: int
    page_count: int | None = None

    title: str | None = None
    author: str | None = None
    language: str | None = None

    extra: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass(slots=True)
class ParsedDocument:
    source: Path

    markdown: str
    text: str

    raw_document: Any

    pages: int | None = None

    metadata: DocumentMetadata | None = None

    validation: Any | None = None


@dataclass(slots=True)
class DocumentInfo:
    document_id: str
    filename: str

    file_type: str

    page_count: int | None = None
    section_count: int = 0
    chunk_count: int = 0

    status: str = "ready"

    metadata: dict[str, Any] = field(
        default_factory=dict
    )