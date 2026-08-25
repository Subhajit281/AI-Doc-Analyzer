from langchain_core.tools import tool


class ReasoningTool:

    def __init__(self):
        self.tool = self._create_tool()

    def _create_tool(self):

        @tool
        def reason_over_context(
            context: str,
            instruction: str,
        ) -> str:
            """
            Perform a controlled analytical operation over supplied context.

            Use this tool when the user's request requires reasoning over
            information rather than simply retrieving or reproducing it.

            Suitable operations include:
            - comparison
            - ranking
            - counting
            - classification
            - evaluation
            - calculation
            - identifying relationships
            - identifying patterns
            - deriving conclusions
            - recommendations based on supplied evidence
            - custom analytical instructions

            The context can contain:
            1. Information retrieved from the document.
            2. Information explicitly supplied by the user.
            3. A mixture of both.

            The analysis must remain grounded in the supplied context.

            Do not invent document facts.
            Do not introduce unsupported external facts.
            Do not treat a user hypothetical as a document fact.
            Derived conclusions are allowed when they logically follow
            from the supplied information.

            If the available context is insufficient to perform the
            requested operation reliably, explicitly report that.
            """

            # =========================================================
            # Input validation
            # =========================================================

            if not context or not context.strip():
                return self._error(
                    "No context was provided for the analysis."
                )

            if not instruction or not instruction.strip():
                return self._error(
                    "No analysis instruction was provided."
                )

            context = context.strip()
            instruction = instruction.strip()

            # =========================================================
            # Detect operation
            # =========================================================

            operation = self._detect_operation(
                instruction
            )

            # =========================================================
            # Build reasoning packet
            # =========================================================

            return self._build_reasoning_packet(
                operation=operation,
                instruction=instruction,
                context=context,
            )

        return reason_over_context

    # =============================================================
    # Operation detection
    # =============================================================

    def _detect_operation(
        self,
        instruction: str,
    ) -> str:

        text = instruction.lower()

        operations = {

            "comparison": [
                "compare",
                "comparison",
                "difference",
                "similar",
                "similarities",
                "contrast",
            ],

            "ranking": [
                "rank",
                "ranking",
                "best",
                "worst",
                "order",
                "prioritize",
                "prioritise",
            ],

            "counting": [
                "how many",
                "count",
                "number of",
                "total number",
            ],

            "classification": [
                "classify",
                "categorize",
                "categorise",
                "category",
                "type of",
            ],

            "evaluation": [
                "evaluate",
                "assess",
                "judge",
                "rate",
                "score",
                "strength",
                "weakness",
            ],

            "calculation": [
                "calculate",
                "compute",
                "percentage",
                "average",
                "sum",
                "difference in",
            ],

            "pattern_analysis": [
                "pattern",
                "trend",
                "relationship",
                "correlation",
                "common",
                "recurring",
            ],

            "recommendation": [
                "recommend",
                "recommendation",
                "suggest",
                "which should",
                "which one should",
            ],
        }

        for operation, keywords in operations.items():

            for keyword in keywords:

                if keyword in text:
                    return operation

        return "custom_analysis"

    # =============================================================
    # Reasoning packet
    # =============================================================

    def _build_reasoning_packet(
        self,
        operation: str,
        instruction: str,
        context: str,
    ) -> str:

        return f"""
REASONING TASK

Operation:
{operation}

Instruction:
{instruction}

SUPPLIED CONTEXT:
{context}

REASONING RULES:

1. Ground the analysis only in the supplied context.

2. Treat information explicitly contained in the supplied
   document evidence as DOCUMENT EVIDENCE.

3. Treat information explicitly introduced by the user as
   USER-PROVIDED CONTEXT or HYPOTHETICAL CONTEXT when applicable.

4. Do not claim that user-provided information came from the
   document.

5. You may derive conclusions that logically follow from the
   supplied information.

6. A derived conclusion does not need to appear verbatim in
   the document.

7. Do not introduce external facts unless they are explicitly
   present in the supplied context.

8. For comparisons, evaluate the entities using only criteria
   supported by the context.

9. For rankings, explain the criteria used for the ranking.

10. For calculations or counts, use only values present in
    the supplied context.

11. If evidence is insufficient, say exactly what is missing
    instead of inventing an answer.

12. Distinguish clearly between:
       - explicit evidence
       - user-provided information
       - derived conclusion

13. Answer the user's actual instruction rather than merely
    repeating the supplied context.

The final response should be concise, evidence-grounded,
and transparent about any assumptions.
""".strip()

    # =============================================================
    # Error response
    # =============================================================

    def _error(
        self,
        message: str,
    ) -> str:

        return (
            "REASONING ERROR\n\n"
            f"{message}"
        )