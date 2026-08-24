from langchain_core.tools import tool


class SearchTool:

    def __init__(
        self,
        vector_store,
        embedder,
        document_id,
    ):
        self.vector_store = vector_store
        self.embedder = embedder
        self.document_id = document_id

        self.tool = self._create_tool()

    def _create_tool(self):

        vector_store = self.vector_store
        embedder = self.embedder
        document_id = self.document_id

        @tool
        def search_documents(query: str) -> str:
            """
            Search the uploaded document for relevant content.

            Use this tool when the user asks about information,
            facts, projects, achievements, technologies, or other
            content contained inside the document.
            """

            # ---------------------------------------------
            # Validate query
            # ---------------------------------------------

            if not query or not query.strip():
                return "Search query cannot be empty."

            # ---------------------------------------------
            # Generate query embedding
            # ---------------------------------------------

            query_embedding = embedder.embed(
                query.strip()
            )

            # ---------------------------------------------
            # Search ONLY inside the current document
            # ---------------------------------------------

            results = vector_store.search(
                query_embedding,
                top_k=5,
                where={
                    "document_id": document_id
                }
            )

            # ---------------------------------------------
            # Handle empty results safely
            # ---------------------------------------------

            documents = results.get(
                "documents",
                [[]]
            )

            metadatas = results.get(
                "metadatas",
                [[]]
            )

            if (
                not documents
                or not documents[0]
            ):
                return (
                    "No relevant information "
                    "was found in the document."
                )

            # ---------------------------------------------
            # Format retrieved evidence
            # ---------------------------------------------

            retrieved = []

            for i, document in enumerate(
                documents[0]
            ):

                metadata = (
                    metadatas[0][i]
                    if metadatas
                    and metadatas[0]
                    and i < len(metadatas[0])
                    else {}
                )

                retrieved.append(
                    f"""
SOURCE {i + 1}
Section: {metadata.get("section", "Unknown")}
Page: {metadata.get("page", "Unknown")}

Content:
{document}
"""
                )

            return "\n".join(
                retrieved
            )

        return search_documents