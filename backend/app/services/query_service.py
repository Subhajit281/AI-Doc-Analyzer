import json

from pathlib import Path
from threading import Lock
from types import SimpleNamespace

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from app.agent.graph import create_agent_graph
from app.llm import get_model_name


# ============================================================
# Paths
# ============================================================

BASE_DIR = Path(
    __file__
).resolve().parents[2]

DOCUMENT_STORAGE = (
    BASE_DIR / "data" / "documents"
)


# ============================================================
# Manifest Helpers
# ============================================================

def _item_from_dict(item_data):

    return SimpleNamespace(

        text=item_data.get(
            "text",
            ""
        ),

        label=item_data.get(
            "label"
        ),

        page=item_data.get(
            "page"
        ),
    )


def _section_from_dict(section_data):

    section = SimpleNamespace(

        title=section_data.get(
            "title",
            ""
        ),

        page=section_data.get(
            "page"
        ),

        level=section_data.get(
            "level",
            0
        ),

        items=[],

        children=[],
    )

    section.items = [

        _item_from_dict(item)

        for item in section_data.get(
            "items",
            []
        )
    ]

    section.children = [

        _section_from_dict(child)

        for child in section_data.get(
            "children",
            []
        )
    ]

    return section


def _load_manifest(
    document_id
):
    from app.core.cache import manifest_cache

def _load_manifest(
    document_id: str,
):
    """
    Load document manifest from in-memory cache, database,
    or fallback directory.
    """

    cached = manifest_cache.get(document_id)
    if cached is not None:
        return cached

    # Attempt to load from MongoDB or local store
    from app.core.database import db_manager
    import asyncio
    import concurrent.futures
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, db_manager.get_document(document_id))
                doc = future.result()
        else:
            doc = asyncio.run(db_manager.get_document(document_id))

        if doc and doc.get("manifest"):
            manifest_data = doc["manifest"]
            manifest_cache.set(document_id, manifest_data)
            return manifest_data
    except Exception as exc:
        print(f"[QUERY] Manifest DB lookup notice: {exc}")

    # Fallback to legacy disk file if present
    document_directory = (
        DOCUMENT_STORAGE
        / document_id
    )

    manifest_path = (
        document_directory
        / "manifest.json"
    )

    if manifest_path.exists():
        try:
            with open(
                manifest_path,
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)
                manifest_cache.set(document_id, data)
                return data
        except Exception:
            pass

    raise FileNotFoundError(
        f"Document '{document_id}' was not found or has expired."
    )


def _build_parsed_document(
    manifest
):

    return SimpleNamespace(

        source=manifest.get(
            "source",
            manifest.get(
                "filename",
                "",
            ),
        ),

        pages=manifest.get(
            "pages",
            0,
        ),
    )


def _build_sections(
    manifest
):

    return [

        _section_from_dict(section)

        for section in manifest.get(
            "sections",
            []
        )
    ]


# ============================================================
# Answer Extraction
# ============================================================

def _extract_answer(
    result
):

    messages = result.get(
        "messages",
        []
    )

    if not messages:

        return (
            "I could not generate an answer."
        )

    for message in reversed(
        messages
    ):

        content = getattr(
            message,
            "content",
            None
        )

        if not content:

            continue

        # ----------------------------------------------------
        # String
        # ----------------------------------------------------

        if isinstance(
            content,
            str
        ):

            return content.strip()

        # ----------------------------------------------------
        # Structured content
        # ----------------------------------------------------

        if isinstance(
            content,
            list
        ):

            parts = []

            for item in content:

                if isinstance(
                    item,
                    str
                ):

                    parts.append(
                        item
                    )

                elif isinstance(
                    item,
                    dict
                ):

                    text = item.get(
                        "text"
                    )

                    if text:

                        parts.append(
                            text
                        )

            if parts:

                return "\n".join(
                    parts
                ).strip()

    return (
        "I could not generate an answer."
    )


# ============================================================
# Query Service
# ============================================================

class QueryService:

    def __init__(self):

        # ----------------------------------------------------
        # Heavy components
        # ----------------------------------------------------

        self.embedder = None

        self.vector_store = None

        # ----------------------------------------------------
        # Initialization lock
        # ----------------------------------------------------

        self._initialization_lock = Lock()

        self._initialized = False

        # ----------------------------------------------------
        # LangGraph conversation memory
        #
        # One shared checkpointer.
        #
        # Conversations are separated using thread_id.
        # ----------------------------------------------------

        self.checkpointer = MemorySaver()

    # ========================================================
    # Initialize RAG Components
    # ========================================================

    def _initialize(
        self
    ):

        if self._initialized:

            return

        with self._initialization_lock:

            if self._initialized:

                return

            print(
                "Initializing query/RAG components..."
            )

            # ------------------------------------------------
            # Heavy imports
            # ------------------------------------------------

            from app.embeddings.embedder import (
                DocumentEmbedder
            )

            from app.vectorstore.chroma_store import (
                ChromaVectorStore
            )

            # ------------------------------------------------
            # Embedder
            # ------------------------------------------------

            print(
                "Loading document embedder..."
            )

            self.embedder = (
                DocumentEmbedder()
            )

            # ------------------------------------------------
            # Vector store
            # ------------------------------------------------

            print(
                "Initializing vector store..."
            )

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
        conversation_id: str,
        is_pro: bool = False,
        manifest: dict | None = None,
    ):

        # ----------------------------------------------------
        # Validate document ID
        # ----------------------------------------------------

        if (
            not document_id
            or not document_id.strip()
        ):

            raise ValueError(
                "Document ID cannot be empty."
            )

        # ----------------------------------------------------
        # Validate query
        # ----------------------------------------------------

        if (
            not query
            or not query.strip()
        ):

            raise ValueError(
                "Query cannot be empty."
            )

        # ----------------------------------------------------
        # Validate conversation ID
        # ----------------------------------------------------

        if (
            not conversation_id
            or not conversation_id.strip()
        ):

            raise ValueError(
                "Conversation ID cannot be empty."
            )

        # ----------------------------------------------------
        # Normalize
        # ----------------------------------------------------

        document_id = (
            document_id.strip()
        )

        query = query.strip()

        conversation_id = (
            conversation_id.strip()
        )

        # ----------------------------------------------------
        # Logging
        # ----------------------------------------------------

        print(
            "\n" + "=" * 80
        )

        print(
            "QUERY STARTED"
        )

        print(
            "Document:",
            document_id
        )

        print(
            "Conversation:",
            conversation_id
        )

        print(
            "Query:",
            query
        )

        print(
            "=" * 80
        )

        # ====================================================
        # Load manifest
        # ====================================================

        if manifest is None:
            manifest = _load_manifest(
                document_id
            )
        else:
            from app.core.cache import manifest_cache
            manifest_cache.set(document_id, manifest)

        # ====================================================
        # Reconstruct document
        # ====================================================

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

        # ====================================================
        # Initialize RAG
        # ====================================================

        self._initialize()

        # ====================================================
        # Build Agent Graph
        #
        # IMPORTANT:
        # We intentionally create it here just like the
        # earlier working version.
        #
        # No graph cache.
        # ====================================================

        graph = create_agent_graph(

            parsed_document=parsed_document,

            sections=sections,

            vector_store=self.vector_store,

            embedder=self.embedder,

            document_id=document_id,

            checkpointer=self.checkpointer,

            is_pro=is_pro,
        )

        # ====================================================
        # Current User Message
        #
        # LangGraph will restore previous messages from
        # MemorySaver using the thread_id.
        # ====================================================

        initial_state = {

            "messages": [

                HumanMessage(
                    content=query
                )

            ],

            "query": query,

            "retrieved_chunks": [],
        }

        # ====================================================
        # Conversation Thread
        # ====================================================

        thread_id = (
            f"{document_id}:"
            f"{conversation_id}"
        )

        print(
            "[QUERY] Thread:",
            thread_id
        )

        # ====================================================
        # Execute Graph
        # ====================================================

        result = graph.invoke(

            initial_state,

            config={
                "configurable": {
                    "thread_id": thread_id
                }
            },
        )

        # ====================================================
        # Extract Answer
        # ====================================================

        answer = _extract_answer(
            result
        )

        print(
            "QUERY COMPLETED"
        )

        print(
            "=" * 80
        )

        # ====================================================
        # Memory Cleanup
        # ====================================================

        from app.core.memory import optimize_memory
        optimize_memory(tag="QueryCompleted")

        return {

            "document_id":
                document_id,

            "conversation_id":
                conversation_id,

            "answer":
                answer,

            "is_pro":
                is_pro,

            "model":
                get_model_name(is_pro=is_pro),
        }


# ============================================================
# Singleton Query Service
# ============================================================

query_service = QueryService()