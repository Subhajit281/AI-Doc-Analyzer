from langchain_core.tools import tool


class EvidenceVerificationTool:

    def __init__(self, llm):

        self.llm = llm
        self.tool = self._create_tool()

    def _create_tool(self):

        llm = self.llm

        @tool
        def verify_evidence(
            claim: str,
            evidence: str
        ) -> str:
            """
            Verify whether provided document evidence supports a claim.

            Use this tool when a claim needs to be checked against
            retrieved document evidence.

            The verification must use only the provided evidence.
            Do not rely on outside knowledge.

            Return:
            - SUPPORTED when the evidence clearly supports the claim.
            - PARTIALLY_SUPPORTED when the evidence supports only
              part of the claim.
            - NOT_SUPPORTED when the evidence does not support the claim.
            """

            if not claim or not claim.strip():
                return "Claim cannot be empty."

            if not evidence or not evidence.strip():
                return "Evidence cannot be empty."

            prompt = f"""
You are an evidence verification system.

Determine whether the provided evidence supports the claim.

Use ONLY the supplied evidence.

VERIFICATION RULES:

1. SUPPORTED
   The evidence clearly supports the claim.

2. PARTIALLY_SUPPORTED
   The evidence supports some part of the claim,
   but not the complete claim.

3. NOT_SUPPORTED
   The evidence does not provide sufficient support
   for the claim.

IMPORTANT:
- Do not use outside knowledge.
- Do not assume missing information.
- Do not treat absence of evidence as proof that something is false.
- Preserve important numbers, dates, names, and terminology.
- Explain exactly which part of the evidence supports
  or fails to support the claim.

CLAIM:
{claim}

EVIDENCE:
{evidence}

Return the result using this format:

VERDICT: <SUPPORTED | PARTIALLY_SUPPORTED | NOT_SUPPORTED>

REASON:
<brief explanation based only on the evidence>
"""

            response = llm.invoke(prompt)

            return response.content

        return verify_evidence