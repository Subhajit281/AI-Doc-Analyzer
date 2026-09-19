from dataclasses import dataclass, field


@dataclass(slots=True)
class DocumentChunk:

    chunk_id: str

    text: str

    document_id: str | None = None

    section: str | None = None
    section_id: str | None = None

    page: int | None = None

    content_type: str = "text"

    chunk_index: int = 0

    token_count: int | None = None

    start_offset: int | None = None
    end_offset: int | None = None

    metadata: dict = field(
        default_factory=dict
    )