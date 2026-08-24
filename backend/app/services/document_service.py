import json
import uuid
from pathlib import Path
from threading import Lock

from fastapi import UploadFile


# ============================================================
# Paths
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DOCUMENT_STORAGE = (
    BASE_DIR / "data" / "documents"
)


# ============================================================
# Section Serialization
# ============================================================

def _section_to_dict(section):
    """
    Convert a DocumentSection hierarchy into
    JSON-serializable data.
    """

    return {
        "title": section.title,
        "page": section.page,
        "level": section.level,

        "items": [
            {
                "text": item.text,
                "label": item.label,
                "page": item.page,
            }
            for item in section.items
        ],

        "children": [
            _section_to_dict(child)
            for child in section.children
        ],
    }


# ============================================================
# Manifest
# ============================================================

def _save_manifest(
    document_id,
    filename,
    parsed_document,
    sections,
):
    """
    Persist lightweight document structure so that
    future queries do not need to run Docling again.
    """

    document_directory = (
        DOCUMENT_STORAGE / document_id
    )

    manifest_path = (
        document_directory / "manifest.json"
    )

    manifest = {
        "document_id": document_id,
        "filename": filename,
        "source": str(parsed_document.source),
        "pages": parsed_document.pages,

        "sections": [
            _section_to_dict(section)
            for section in sections
        ],
    }

    with open(
        manifest_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            manifest,
            file,
            indent=2,
            ensure_ascii=False,
        )


# ============================================================
# Document Service
# ============================================================

class DocumentService:

    def __init__(self):

        # ----------------------------------------------------
        # IMPORTANT:
        # Do NOT initialize heavy ML components here.
        #
        # This constructor runs when the application imports
        # this module.
        # ----------------------------------------------------

        self.validator = None
        self.parser = None
        self.extractor = None
        self.chunker = None
        self.embedder = None
        self.vector_store = None

        # Prevent multiple simultaneous initializations
        # if multiple requests arrive at startup.
        self._initialization_lock = Lock()

        self._initialized = False

    # ========================================================
    # Lazy Initialization
    # ========================================================

    def _initialize(self):
        """
        Initialize heavy document-processing components
        only when they are actually needed.

        This keeps FastAPI startup fast enough for platforms
        such as Render to detect the application port.
        """

        if self._initialized:
            return

        with self._initialization_lock:

            # Another request may have initialized everything
            # while this request was waiting for the lock.
            if self._initialized:
                return

            print(
                "Initializing document processing pipeline..."
            )

            # ------------------------------------------------
            # Import heavy modules only when required.
            # ------------------------------------------------

            from app.validation.validator import (
                DocumentValidator,
            )

            from app.parser.docling_parser import (
                DoclingParser,
            )

            from app.sections.extractor import (
                SectionExtractor,
            )

            from app.chunking.chunker import (
                DocumentChunker,
            )

            from app.embeddings.embedder import (
                DocumentEmbedder,
            )

            from app.vectorstore.chroma_store import (
                ChromaVectorStore,
            )

            # ------------------------------------------------
            # Initialize components
            # ------------------------------------------------

            self.validator = DocumentValidator()

            self.parser = DoclingParser()

            self.extractor = SectionExtractor()

            self.chunker = DocumentChunker()

            self.embedder = DocumentEmbedder()

            self.vector_store = ChromaVectorStore()

            self._initialized = True

            print(
                "Document processing pipeline initialized."
            )

    # ========================================================
    # Process Document
    # ========================================================

    async def process_document(
        self,
        file: UploadFile,
    ):

        # ====================================================
        # Initialize heavy components only when a document
        # actually needs to be processed.
        # ====================================================

        self._initialize()

        # ====================================================
        # 1. Generate document ID
        # ====================================================

        document_id = str(
            uuid.uuid4()
        )

        # ====================================================
        # 2. Create document directory
        # ====================================================

        document_directory = (
            DOCUMENT_STORAGE / document_id
        )

        document_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ====================================================
        # 3. Save uploaded file
        # ====================================================

        if not file.filename:

            raise ValueError(
                "Uploaded file must have a filename."
            )

        # Prevent path traversal
        filename = Path(
            file.filename
        ).name

        file_path = (
            document_directory / filename
        )

        contents = await file.read()

        if not contents:

            raise ValueError(
                "Uploaded document is empty."
            )

        with open(
            file_path,
            "wb",
        ) as buffer:

            buffer.write(contents)

        # ====================================================
        # 4. Validate document
        # ====================================================

        validation = (
            self.validator.validate(
                file_path
            )
        )

        # ====================================================
        # 5. Parse with Docling
        # ====================================================

        parsed_document = (
            self.parser.parse(
                file_path,
                validation,
            )
        )

        # ====================================================
        # 6. Extract document sections
        # ====================================================

        sections = (
            self.extractor.extract(
                parsed_document.raw_document
            )
        )

        # ====================================================
        # 7. Persist document structure
        # ====================================================

        _save_manifest(
            document_id=document_id,
            filename=filename,
            parsed_document=parsed_document,
            sections=sections,
        )

        # ====================================================
        # 8. Create structure-aware chunks
        # ====================================================

        chunks = (
            self.chunker.chunk(
                sections
            )
        )

        if not chunks:

            raise ValueError(
                "No usable content could be "
                "extracted from the document."
            )

        # ====================================================
        # 9. Generate embeddings
        # ====================================================

        texts = [
            chunk.text
            for chunk in chunks
        ]

        embeddings = (
            self.embedder.embed_many(
                texts
            )
        )

        # ====================================================
        # 10. Prepare ChromaDB records
        # ====================================================

        ids = []

        metadatas = []

        for chunk in chunks:

            # ----------------------------------------------
            # Unique vector ID
            # ----------------------------------------------

            chunk_id = (
                f"{document_id}_{chunk.chunk_id}"
            )

            ids.append(
                chunk_id
            )

            # ----------------------------------------------
            # Metadata
            # ----------------------------------------------

            metadatas.append({

                "document_id": (
                    document_id
                ),

                "chunk_id": str(
                    chunk.chunk_id
                ),

                "section": (
                    chunk.section
                ),

                "page": (
                    chunk.page
                    if chunk.page is not None
                    else -1
                ),

                "content_type": (
                    chunk.content_type
                ),

                "parent_section": (
                    chunk.parent_section
                    or ""
                ),

                "section_path": (
                    chunk.section_path
                    or ""
                ),

                "source": (
                    filename
                ),
            })

        # ====================================================
        # 11. Store vectors in ChromaDB
        # ====================================================

        self.vector_store.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        # ====================================================
        # 12. Return document information
        # ====================================================

        return {

            "document_id": (
                document_id
            ),

            "filename": (
                filename
            ),

            "status": (
                "ready"
            ),

            "page_count": (
                parsed_document.pages
            ),

            "section_count": (
                len(sections)
            ),

            "chunk_count": (
                len(chunks)
            ),
        }


# ============================================================
# Singleton Service
# ============================================================

# This is now SAFE.
#
# It only creates the lightweight DocumentService object.
# Heavy ML components are NOT loaded here.
#
document_service = DocumentService()


# ============================================================
# Public Function
# ============================================================

async def process_document(
    file: UploadFile,
):

    return await (
        document_service.process_document(
            file
        )
    )