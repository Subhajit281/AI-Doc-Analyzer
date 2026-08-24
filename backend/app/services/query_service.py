import json
from pathlib import Path
from types import SimpleNamespace

from langchain_core.messages import HumanMessage

from app.agent.graph import create_agent_graph
from app.embeddings.embedder import DocumentEmbedder
from app.vectorstore.chroma_store import ChromaVectorStore
from app.sections.extractor import (
    DocumentSection,
    DocumentElement,
)


# ============================================================
# Paths
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DOCUMENT_STORAGE = (
    BASE_DIR / "data" / "documents"
)


class QueryService:

    def __init__(self):

        # These are intentionally lazy.
        # We don't want to load the embedding model
        # when the backend starts.

        self.embedder = None
        self.vector_store = None

    # ========================================================
    # Initialize query components
    # ========================================================

    def _initialize(self):

        if self.embedder is None:

            print(
                "Loading embedding model for queries..."
            )

            self.embedder = DocumentEmbedder()

            print(
                "✓ Query embedding model loaded"
            )

        if self.vector_store is None:

            self.vector_store = (
                ChromaVectorStore()
            )

            print(
                "✓ ChromaDB connected"
            )

    # ========================================================
    # Load manifest
    # ========================================================

    def _load_manifest(
        self,
        document_id: str,
    ):

        document_directory = (
            DOCUMENT_STORAGE / document_id
        )

        manifest_path = (
            document_directory / "manifest.json"
        )

        if not document_directory.exists():

            raise FileNotFoundError(
                f"Document '{document_id}' was not found."
            )

        if not manifest_path.exists():

            raise FileNotFoundError(
                "Document manifest is missing."
            )

        try:

            with open(
                manifest_path,
                "r",
                encoding="utf-8",
            ) as file:

                manifest = json.load(file)

        except json.JSONDecodeError as exc:

            raise ValueError(
                "Document manifest is corrupted."
            ) from exc

        return manifest

    # ========================================================
    # Restore DocumentSection
    # ========================================================

    def _restore_section(
        self,
        data,
        parent=None,
    ):
        """
        Reconstruct a DocumentSection object from
        the JSON representation stored during upload.
        """

        items = []

        for item in data.get(
            "items",
            []
        ):

            items.append(
                DocumentElement(
                    text=item.get(
                        "text",
                        ""
                    ),
                    label=item.get(
                        "label",
                        "unknown"
                    ),
                    page=item.get(
                        "page"
                    ),
                )
            )

        section = DocumentSection(
            title=data.get(
                "title",
                ""
            ),
            items=items,
            page=data.get(
                "page"
            ),
            level=data.get(
                "level",
                1
            ),
            parent=parent,
        )

        # Restore child hierarchy

        for child_data in data.get(
            "children",
            []
        ):

            child = self._restore_section(
                child_data,
                parent=section,
            )

            section.children.append(
                child
            )

        return section

    # ========================================================
    # Restore all sections
    # ========================================================

    def _restore_sections(
        self,
        manifest,
    ):

        sections = []

        for section_data in manifest.get(
            "sections",
            []
        ):

            section = self._restore_section(
                section_data
            )

            sections.append(
                section
            )

        return sections

    # ========================================================
    # Create lightweight parsed document
    # ========================================================

    def _restore_parsed_document(
        self,
        manifest,
    ):
        """
        Recreate only the fields required by the
        existing agent tools.

        We deliberately do NOT recreate the full
        Docling document.
        """

        source = manifest.get(
            "source"
        )

        pages = manifest.get(
            "pages",
            0
        )

        return SimpleNamespace(
            source=Path(source)
            if source
            else Path(
                manifest.get(
                    "filename",
                    "unknown"
                )
            ),
            pages=pages,
        )

    # ========================================================
    # Execute query
    # ========================================================

    def query(
        self,
        document_id: str,
        query: str,
    ):

        # ----------------------------------------------------
        # Validate query
        # ----------------------------------------------------

        if not query or not query.strip():

            raise ValueError(
                "Query cannot be empty."
            )

        query = query.strip()

        # ----------------------------------------------------
        # Validate document and load manifest
        # ----------------------------------------------------

        manifest = self._load_manifest(
            document_id
        )

        # ----------------------------------------------------
        # Restore persisted document state
        # ----------------------------------------------------

        sections = self._restore_sections(
            manifest
        )

        parsed_document = (
            self._restore_parsed_document(
                manifest
            )
        )

        # ----------------------------------------------------
        # Initialize vector search components
        # ----------------------------------------------------

        self._initialize()

        # ----------------------------------------------------
        # Create the existing Agentic RAG graph
        # ----------------------------------------------------

        graph = create_agent_graph(
            parsed_document=parsed_document,
            sections=sections,
            vector_store=self.vector_store,
            embedder=self.embedder,
            document_id=document_id,
        )

        # ----------------------------------------------------
        # Initial LangGraph state
        # ----------------------------------------------------

        initial_state = {
            "messages": [
                HumanMessage(
                    content=query
                )
            ],

            "query": query,

            "retrieved_chunks": [],
        }

        # ----------------------------------------------------
        # Execute agent
        # ----------------------------------------------------

        result = graph.invoke(
            initial_state
        )

        # ----------------------------------------------------
        # Extract messages
        # ----------------------------------------------------

        messages = result.get(
            "messages",
            []
        )

        if not messages:

            raise RuntimeError(
                "Agent returned no messages."
            )

        # ----------------------------------------------------
        # Find final assistant response
        # ----------------------------------------------------

        final_message = messages[-1]

        answer = getattr(
            final_message,
            "content",
            None
        )

        if not answer:

            raise RuntimeError(
                "Agent returned an empty response."
            )

        # ----------------------------------------------------
        # Return API-ready result
        # ----------------------------------------------------

        return {
            "document_id": document_id,
            "filename": manifest.get(
                "filename"
            ),
            "answer": answer,
        }


# ============================================================
# Singleton
# ============================================================

query_service = QueryService()