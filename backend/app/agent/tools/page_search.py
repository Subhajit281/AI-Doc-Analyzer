from langchain_core.tools import tool


class PageSearchTool:

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
        def search_by_page(
            page: int,
            query: str
        ) -> str:
            """
            Search the uploaded document for relevant content
            restricted to a specific page.

            Use this tool when the user explicitly refers to
            a particular page and asks about information on that page.
            """

            # ---------------------------------------------
            # Validate page
            # ---------------------------------------------

            if page < 1:
                return (
                    "Page number must be greater than 0."
                )

            # ---------------------------------------------
            # Validate query
            # ---------------------------------------------

            if not query or not query.strip():
                return (
                    "Search query cannot be empty."
                )

            # ---------------------------------------------
            # Generate query embedding
            # ---------------------------------------------

            query_embedding = embedder.embed(
                query.strip()
            )

            # ---------------------------------------------
            # Search only inside the current document
            # and requested page
            # ---------------------------------------------

            results = vector_store.search(
                query_embedding,
                top_k=5,
                where={
                    "$and": [
                        {
                            "document_id": document_id
                        },
                        {
                            "page": page
                        }
                    ]
                }
            )

            # ---------------------------------------------
            # Safely extract results
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
                    f"No relevant information found "
                    f"on page {page}."
                )

            # ---------------------------------------------
            # Format retrieved evidence
            # ---------------------------------------------

            retrieved = []

            for i, document in enumerate(
                documents[0]
            ):

                if (
                    metadatas
                    and metadatas[0]
                    and i < len(metadatas[0])
                ):
                    metadata = (
                        metadatas[0][i]
                    )
                else:
                    metadata = {}

                retrieved.append(
                    f"""
SOURCE {i + 1}
Section: {metadata.get("section", "Unknown")}
Page: {metadata.get("page", page)}

Content:
{document}
"""
                )

            # ---------------------------------------------
            # Return evidence
            # ---------------------------------------------

            return "\n".join(
                retrieved
            )

        return search_by_page