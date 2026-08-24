from langchain_core.tools import tool


def create_section_tool(sections):

    @tool
    def get_section(section_name: str) -> str:
        """
        Retrieve the content of a specific section from the document.

        Use this tool when the user asks about a named section
        such as Technical Skills, Projects, Achievements,
        Interests, or another section.
        """

        if not section_name or not section_name.strip():
            return "Section name cannot be empty."

        requested_name = section_name.strip().lower()

        # Exact match
        for section in sections:
            if section.title.strip().lower() == requested_name:
                return _format_section(section)

        # Partial match
        for section in sections:
            title = section.title.strip().lower()

            if requested_name in title or title in requested_name:
                return _format_section(section)

        available_sections = ", ".join(
            section.title for section in sections
        )

        return (
            f"Section '{section_name}' was not found.\n"
            f"Available sections: {available_sections}"
        )

    return get_section


def _format_section(section) -> str:
    """Convert a DocumentSection into text for the LLM."""

    lines = [
        f"Section: {section.title}",
        f"Page: {section.page}",
        "",
    ]

    for item in section.items:
        if hasattr(item, "text") and item.text:
            lines.append(item.text.strip())

    return "\n".join(lines)