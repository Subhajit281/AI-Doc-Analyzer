import json
from pathlib import Path
from threading import Lock
from types import SimpleNamespace

from langchain_core.messages import HumanMessage

from app.agent.graph import create_agent_graph


# ============================================================
# Paths
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DOCUMENT_STORAGE = (
    BASE_DIR / "data" / "documents"
)


# ============================================================
# Helpers
# ============================================================

def _item_from_dict(item_data):
    """
    Reconstruct a lightweight document item from
    the serialized manifest representation.
    """

    return SimpleNamespace(
        text=item_data.get("text", ""),
        label=item_data.get("label"),
        page=item_data.get("page"),
    )


def _section_from_dict(section_data):
    """
    Reconstruct a DocumentSection-compatible object
    from manifest.json.

    The agent tools only require the section attributes,
    so SimpleNamespace is sufficient here.
    """

    section = SimpleNamespace(
        title=section_data.get("title", ""),
        page=section_data.get("page"),
        level=section_data.get("level", 0),
        items=[],
        children=[],
    )

    section.items = [
        _item_from_dict(item)
        for item in section_data.get("items", [])
    ]

    section.children = [
        _section_from_dict(child)
        for child in section_data.get("children", [])
    ]

    return section


def _load_manifest(document_id):
    """
    Load the persisted document structure.

    The manifest is created during document upload,
    so querying does not require running Docling again.
    """

    document_directory = (
        DOCUMENT_STORAGE / document_id
    )

    manifest_path = (
        document_directory / "manifest.json"
    )

    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Document '{document_id}' was not found."
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


def _build_parsed_document(manifest):
    """
    Reconstruct the lightweight parsed-document
    object required by MetadataTool.
    """

    return SimpleNamespace(
        source=manifest.get(
            "source",
            manifest.get("filename", ""),
        ),
        pages=manifest.get(
            "pages",
            0,
        ),
    )


def _build_sections(manifest):
    """
    Reconstruct the section hierarchy from
    manifest.json.
    """

    return [
        _section_from_dict(section)
        for section in manifest.get(
            "sections",
            [],
        )
    ]


def _extract_answer(result):
    """
    Extract the final assistant response from
    the LangGraph state.
    """

    messages = result.get(
        "messages",
        [],
    )

    if not messages:
        return "I could not generate an answer."

    # Walk backwards because the final message should
    # contain the agent's final response.
    for message in reversed(messages):

        content = getattr(
            message,
            "content",
            None,
        )

        if content:

            # Gemini/LangChain normally returns a string.
            if isinstance(content, str):
                return content.strip()

            # Some providers may return structured content.
            if isinstance(content, list):

                text_parts = []

                for part in content:

                    if isinstance(part, str):
                        text_parts.append(part)

                    elif isinstance(part, dict):

                        text = part.get("text")

                        if text:
                            text_parts.append(text)

                if text_parts:
                    return "\n".join(
                        text_parts
                    ).strip()

    return "I could not generate an answer."


# ============================================================
# Query Service
# ============================================================

class QueryService:

    def __init__(self):

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # Do NOT initialize the embedding model, Chroma,
        # Gemini, or LangGraph here.
        #
        # This object is imported while FastAPI starts.
        # ----------------------------------------------------

        self.embedder = None
        self.vector_store = None

        self._initialization_lock = Lock()

        self._initialized = False

    # ========================================================
    # Lazy Initialization
    # ========================================================

    def _initialize(self):
        """
        Initialize query-time RAG components only when
        the first query is received.

        This prevents Render from blocking during startup.
        """

        if self._initialized:
            return

        with self._initialization_lock:

            if self._initialized:
                return

            print(
                "Initializing query/RAG components..."
            )

            # ------------------------------------------------
            # Heavy imports happen only here.
            # ------------------------------------------------

            from app.embeddings.embedder import (
                DocumentEmbedder,
            )

            from app.vectorstore.chroma_store import (
                ChromaVectorStore,
            )

            # ------------------------------------------------
            # Initialize components.
            # ------------------------------------------------

            self.embedder = DocumentEmbedder()

            self.vector_store = (
                ChromaVectorStore()
            )

            self._initialized = True

            print(
                "Query/RAG components initialized."
            )

    # ========================================================
    # Query
    # ========================================================

    def query(
        self,
        document_id: str,
        query: str,
    ):
        """
        Execute an Agentic RAG query against a
        previously uploaded document.
        """

        # ----------------------------------------------------
        # Validate inputs
        # ----------------------------------------------------

        if not document_id or not document_id.strip():

            raise ValueError(
                "Document ID cannot be empty."
            )

        if not query or not query.strip():

            raise ValueError(
                "Query cannot be empty."
            )

        document_id = document_id.strip()
        query = query.strip()

        # ----------------------------------------------------
        # Make sure document exists BEFORE initializing
        # expensive query components.
        # ----------------------------------------------------

        manifest = _load_manifest(
            document_id
        )

        # ----------------------------------------------------
        # Reconstruct document structure.
        # ----------------------------------------------------

        parsed_document = (
            _build_parsed_document(
                manifest
            )
        )

        sections = _build_sections(
            manifest
        )

        if not sections:

            raise ValueError(
                "No document sections are available "
                "for this document."
            )

        # ----------------------------------------------------
        # Initialize query components.
        # ----------------------------------------------------

        self._initialize()

        # ----------------------------------------------------
        # Create Agentic RAG graph.
        #
        # The graph receives the current document's
        # parsed structure, sections, vector store,
        # embedder, and document ID.
        # ----------------------------------------------------

        graph = create_agent_graph(
            parsed_document=parsed_document,
            sections=sections,
            vector_store=self.vector_store,
            embedder=self.embedder,
            document_id=document_id,
        )

        # ----------------------------------------------------
        # Initial AgentState
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
        # Execute Agentic RAG
        # ----------------------------------------------------

        result = graph.invoke(
            initial_state
        )

        # ----------------------------------------------------
        # Extract final answer.
        # ----------------------------------------------------

        answer = _extract_answer(
            result
        )

        return {
            "document_id": document_id,
            "answer": answer,
        }


# ============================================================
# Singleton
# ============================================================

query_service = QueryService()