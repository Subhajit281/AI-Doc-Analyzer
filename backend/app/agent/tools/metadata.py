from langchain_core.tools import tool


class MetadataTool:

    def __init__(self, parsed_document, sections):
        self.parsed_document = parsed_document
        self.sections = sections

        self.tool = self._create_tool()

    def _create_tool(self):

        parsed_document = self.parsed_document
        sections = self.sections

        @tool
        def get_document_metadata() -> str:
            """
            Get structural information about the currently loaded document.

            Use this tool when the user asks about:
            - number of pages
            - document source
            - available sections
            - document structure

            Do not use this tool for questions about the actual
            content inside the document.
            """

            section_names = []

            for section in sections:
                if section.title:
                    section_names.append(section.title)

            return (
                f"Source: {parsed_document.source}\n"
                f"Pages: {parsed_document.pages}\n"
                f"Sections: {', '.join(section_names)}"
            )

        return get_document_metadata