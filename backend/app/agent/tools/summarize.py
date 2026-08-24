from langchain_core.tools import tool


class SummarizeSectionTool:

    def __init__(self, sections, llm):

        self.sections = sections
        self.llm = llm

        self.tool = self._create_tool()

    def _create_tool(self):

        sections = self.sections
        llm = self.llm

        @tool
        def summarize_section(
            section_name: str,
            instruction: str = "Summarize this section concisely."
        ) -> str:
            """
            Summarize a specific section of the currently loaded document.

            Use this tool when the user asks for a summary,
            overview, key points, or concise explanation of a
            particular document section.

            The summary must be based only on the content of
            the requested section.
            """

            if not section_name or not section_name.strip():
                return "Section name cannot be empty."

            section = _find_section(
                sections,
                section_name
            )

            if section is None:
                available_sections = ", ".join(
                    s.title for s in sections
                )

                return (
                    f"Section '{section_name}' was not found.\n"
                    f"Available sections: {available_sections}"
                )

            content = _format_section(section)

            prompt = f"""
You are a document summarization system.

Summarize the provided document section according to the
user's instruction.

IMPORTANT RULES:
- Use ONLY the provided section content.
- Do not invent facts.
- Do not introduce information from outside the section.
- Preserve important names, dates, numbers, and terminology.
- Keep the summary faithful to the source.
- If the section contains insufficient information, say so.

USER INSTRUCTION:
{instruction}

SECTION:
{content}
"""

            response = llm.invoke(prompt)

            return response.content

        return summarize_section


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