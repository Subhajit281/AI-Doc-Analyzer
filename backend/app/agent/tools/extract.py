
from langchain_core.tools import tool


class InformationExtractionTool:

    def __init__(self, llm):
        self.llm = llm

        self.tool = self._create_tool()

    def _create_tool(self):

        llm = self.llm

        @tool
        def extract_information(
            evidence: str,
            instruction: str
        ) -> str:
            """
            Extract specific information from provided document evidence.

            Use this tool when information has already been retrieved
            from the document and needs to be transformed into structured,
            concise, factual information.

            The extraction must be based only on the provided evidence.
            Do not invent or infer information that is not supported
            by the evidence.

            Args:
                evidence: Relevant content retrieved from the document.
                instruction: What information should be extracted.
            """

            if not evidence or not evidence.strip():
                return "No evidence was provided."

            if not instruction or not instruction.strip():
                return "Extraction instruction cannot be empty."

            prompt = f"""
You are a document information extraction system.

Extract information from the provided evidence according to the
instruction.

IMPORTANT RULES:
- Use ONLY the provided evidence.
- Do not invent facts.
- Do not add information from outside the evidence.
- Preserve important names, numbers, dates, and terminology.
- If the requested information is not present, explicitly say so.
- Return the extracted information clearly and concisely.

INSTRUCTION:
{instruction}

EVIDENCE:
{evidence}
"""

            response = llm.invoke(prompt)

            return response.content

        return extract_information