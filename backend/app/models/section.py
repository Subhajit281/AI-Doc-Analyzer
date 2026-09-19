from dataclasses import dataclass, field


@dataclass(slots=True)
class DocumentElement:
    text: str
    label: str

    page: int | None = None

    element_id: str | None = None

    metadata: dict = field(
        default_factory=dict
    )


@dataclass(slots=True)
class DocumentSection:
    title: str

    items: list[DocumentElement] = field(
        default_factory=list
    )

    page: int | None = None

    level: int = 1

    section_id: str | None = None

    parent_id: str | None = None

    children_ids: list[str] = field(
        default_factory=list
    )

    metadata: dict = field(
        default_factory=dict
    )

    @property
    def text(self) -> str:
        return "\n".join(
            item.text
            for item in self.items
            if item.text
        )

    @property
    def item_count(self) -> int:
        return len(self.items)