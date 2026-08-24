from dataclasses import dataclass, field
from typing import List


@dataclass
class DocumentElement:
    text: str
    label: str
    page: int | None = None


@dataclass
class DocumentSection:
    title: str
    items: List[DocumentElement]
    page: int | None = None
    level: int = 1

    parent: "DocumentSection | None" = None
    children: List["DocumentSection"] = field(
        default_factory=list
    )


class SectionExtractor:

    def extract(
        self,
        document
    ) -> List[DocumentSection]:

        roots = []

        # Stack containing the current hierarchy.
        #
        # stack[0] -> level 1
        # stack[1] -> level 2
        # stack[2] -> level 3
        #
        stack = []

        for item, level in document.iterate_items():

            item_level = self._get_level(
                item,
                level
            )

            # -----------------------------------------
            # Heading
            # -----------------------------------------

            if self._is_heading(item):

                title = self._extract_text(item)

                if not title:
                    continue

                section = DocumentSection(
                    title=title,
                    items=[],
                    page=self._get_page(item),
                    level=item_level
                )

                # -------------------------------------
                # Remove previous sections at the
                # same/deeper level.
                # -------------------------------------

                while len(stack) >= item_level:
                    stack.pop()

                # -------------------------------------
                # Find parent
                # -------------------------------------

                if stack:

                    parent = stack[-1]

                    section.parent = parent

                    parent.children.append(
                        section
                    )

                else:

                    # No parent = root section
                    roots.append(section)

                # -------------------------------------
                # Put current section on stack
                # -------------------------------------

                stack.append(section)

                continue

            # -----------------------------------------
            # Content belongs to current section
            # -----------------------------------------

            if not stack:
                continue

            element = self._normalize_item(
                item
            )

            if element is not None:

                current_section = stack[-1]

                current_section.items.append(
                    element
                )

        return roots

    # =================================================
    # Heading
    # =================================================

    def _is_heading(
        self,
        item
    ) -> bool:

        return (
            getattr(
                item,
                "label",
                ""
            )
            == "section_header"
        )

    # =================================================
    # Level
    # =================================================

    def _get_level(
        self,
        item,
        level
    ) -> int:

        item_level = getattr(
            item,
            "level",
            None
        )

        if item_level is not None:
            return int(item_level)

        if level is not None:
            return int(level)

        return 1

    # =================================================
    # Normalize item
    # =================================================

    def _normalize_item(
        self,
        item
    ) -> DocumentElement | None:

        label = str(
            getattr(
                item,
                "label",
                "unknown"
            )
        )

        page = self._get_page(item)

        text = self._extract_text(item)

        if text:

            return DocumentElement(
                text=text,
                label=label,
                page=page
            )

        if label == "table":

            text = self._extract_table(item)

            if text:

                return DocumentElement(
                    text=text,
                    label="table",
                    page=page
                )

        return None

    # =================================================
    # Text
    # =================================================

    def _extract_text(
        self,
        item
    ) -> str:

        text = getattr(
            item,
            "text",
            None
        )

        if text:
            return str(text).strip()

        return ""

    # =================================================
    # Table
    # =================================================

    def _extract_table(
        self,
        item
    ) -> str:

        for method_name in (
            "export_to_markdown",
            "export_to_dataframe",
        ):

            method = getattr(
                item,
                method_name,
                None
            )

            if not callable(method):
                continue

            try:

                result = method()

                if result is None:
                    continue

                if method_name == "export_to_dataframe":

                    return result.to_markdown(
                        index=False
                    )

                return str(
                    result
                ).strip()

            except Exception:
                continue

        return ""

    # =================================================
    # Page
    # =================================================

    def _get_page(
        self,
        item
    ) -> int | None:

        prov = getattr(
            item,
            "prov",
            None
        )

        if not prov:
            return None

        return getattr(
            prov[0],
            "page_no",
            None
        )