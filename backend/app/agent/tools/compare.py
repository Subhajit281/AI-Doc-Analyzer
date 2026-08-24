from langchain_core.tools import tool


class CompareSectionsTool:

    def __init__(self, sections, llm):

        self.sections = sections
        self.llm = llm

        self.tool = self._create_tool()

    def _create_tool(self):

        sections = self.sections
        llm = self.llm

        @tool
        def compare_sections(
            section_a: str,
            section_b: str,
            instruction: str = "Compare the two sections."
        ) -> str:
            """
            Compare two sections of the currently loaded document.

            Use this tool when the user asks to compare, contrast,
            identify similarities, identify differences, or analyze
            relationships between two document sections.

            The comparison must be based only on the actual content
            of the two requested sections.
            """

            if not section_a.strip():
                return "First section name cannot be empty."

            if not section_b.strip():
                return "Second section name cannot be empty."

            section_a_data = _find_section(
                sections,
                section_a
            )

            section_b_data = _find_section(
                sections,
                section_b
            )

            if section_a_data is None:
                return f"Section '{section_a}' was not found."

            if section_b_data is None:
                return f"Section '{section_b}' was not found."

            content_a = _format_section(
                section_a_data
            )

            content_b = _format_section(
                section_b_data
            )

            prompt = f"""
You are comparing two sections from the same document.

Compare them according to the user's instruction.

IMPORTANT:
- Use only the provided section contents.
- Do not invent information.
- Clearly distinguish similarities and differences.
- If something is not present, say so.
- Preserve important names, dates, numbers, and terminology.

USER INSTRUCTION:
{instruction}

SECTION A:
{content_a}

SECTION B:
{content_b}
"""

            response = llm.invoke(prompt)

            return response.content

        return compare_sections


def _find_section(sections, section_name):

    requested = section_name.strip().lower()

    # Exact match
    for section in sections:
        if section.title.strip().lower() == requested:
            return section

    # Partial match
    for section in sections:
        title = section.title.strip().lower()

        if requested in title or title in requested:
            return section

    return None


def _format_section(section):

    lines = [
        f"Section: {section.title}",
        f"Page: {section.page}",
        "",
    ]

    for item in section.items:
        if hasattr(item, "text") and item.text:
            lines.append(item.text.strip())

    return "\n".join(lines)