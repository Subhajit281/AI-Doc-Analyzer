import json
import uuid
import tempfile
from datetime import datetime, timezone, timedelta
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
# Manifest Builder
# ============================================================

def _build_manifest(
    document_id,
    filename,
    parsed_document,
    sections,
):
    """
    Build lightweight document structure for database storage
    and in-memory caching so that future queries do not need
    to re-parse the document.
    """

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

    # In-memory cache for subsequent queries
    from app.core.cache import manifest_cache
    manifest_cache.set(document_id, manifest)

    return manifest


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

            from app.parser.factory import (
                get_document_parser,
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

            self.parser = get_document_parser()

            self.extractor = SectionExtractor()

            self.chunker = DocumentChunker()

            self.embedder = DocumentEmbedder()

            self.vector_store = ChromaVectorStore()

            self._initialized = True

            print(
                "Document processing pipeline initialized."
            )

    # ========================================================
    # Process Document (Queue-Protected)
    # ========================================================

    async def process_document(
        self,
        file: UploadFile,
        user_id: str,
    ):
        from app.core.queue import ingestion_queue

        async def _execute_ingestion():
            return await self._process_document_internal(file, user_id)

        filename = file.filename or "unknown"
        return await ingestion_queue.execute(
            _execute_ingestion,
            task_name=f"Ingest-{filename}",
        )

    async def _process_document_internal(
        self,
        file: UploadFile,
        user_id: str,
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
        # 2. Read & Validate Uploaded File
        # ====================================================

        if not file.filename:
            raise ValueError(
                "Uploaded file must have a filename."
            )

        # Prevent path traversal
        filename = Path(
            file.filename
        ).name

        contents = await file.read()

        if not contents:
            raise ValueError(
                "Uploaded document is empty."
            )

        if len(contents) > 10 * 1024 * 1024:
            raise ValueError(
                "File size exceeds the 10 MB upload limit."
            )

        # ====================================================
        # 3. Process via Transient Scratch File
        # No permanent files remain in project directory!
        # ====================================================

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            temp_file_path = Path(temp_dir) / filename

            with open(
                temp_file_path,
                "wb",
            ) as buffer:
                buffer.write(contents)

            # Validate document
            validation = (
                self.validator.validate(
                    temp_file_path
                )
            )

            # Parse with Docling / PyPDF
            parsed_document = (
                self.parser.parse(
                    temp_file_path,
                    validation,
                )
            )

            # Extract document sections
            sections = (
                self.extractor.extract(
                    parsed_document.raw_document
                )
            )

            # Proactively unlink temp file and collect garbage to release OS file locks
            try:
                import gc
                gc.collect()
                if temp_file_path.exists():
                    temp_file_path.unlink(missing_ok=True)
            except Exception:
                pass

        # ====================================================
        # 4. Build Document Manifest
        # ====================================================

        manifest = _build_manifest(
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
        # 12. Save Document Record to Database
        # Stored in user's account with 7-day TTL expiration!
        # ====================================================

        from app.core.database import db_manager
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=7)

        doc_record = {
            "document_id": document_id,
            "user_id": user_id,
            "filename": filename,
            "content_type": file.content_type or "application/octet-stream",
            "file_size": len(contents),
            "file_bytes": contents,
            "manifest": manifest,
            "page_count": parsed_document.pages,
            "section_count": len(sections),
            "chunk_count": len(chunks),
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "expires_at_dt": expires_at,
        }
        await db_manager.save_document(doc_record)

        # ====================================================
        # 13. Memory cleanup
        # ====================================================

        from app.core.memory import optimize_memory
        optimize_memory(tag=f"UploadCompleted-{document_id[:8]}")

        # ====================================================
        # 14. Return document information
        # ====================================================

        return {
            "document_id": document_id,
            "filename": filename,
            "status": "ready",
            "page_count": parsed_document.pages,
            "section_count": len(sections),
            "chunk_count": len(chunks),
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "days_remaining": 7,
            "expiry_label": "Expires in 7d",
        }

    # ========================================================
    # Delete Document
    # ========================================================

    async def delete_document(
        self,
        document_id: str,
        user_id: str,
    ) -> dict:
        import shutil
        from app.core.cache import manifest_cache
        from app.core.memory import optimize_memory
        from app.core.database import db_manager

        # 1. Delete from database (verifying ownership)
        deleted_from_db = await db_manager.delete_document(document_id, user_id)
        if not deleted_from_db:
            existing = await db_manager.get_document(document_id)
            if existing and existing.get("user_id") != user_id:
                raise PermissionError("You do not have permission to delete this document.")

        # 2. In-memory cache invalidation
        manifest_cache.delete(document_id)

        # 3. Purge vector embeddings from ChromaDB
        self._initialize()
        if self.vector_store is not None:
            try:
                self.vector_store.collection.delete(
                    where={"document_id": document_id}
                )
            except Exception:
                pass

        # 4. Clean up any legacy disk folder if one existed
        legacy_dir = DOCUMENT_STORAGE / document_id
        if legacy_dir.exists():
            shutil.rmtree(legacy_dir, ignore_errors=True)

        optimize_memory(tag=f"DeleteDoc-{document_id[:8]}")

        return {
            "document_id": document_id,
            "status": "deleted",
        }


# ============================================================
# Singleton Service
# ============================================================

# This is now SAFE.
# It only creates the lightweight DocumentService object.
# Heavy ML components are NOT loaded here.
document_service = DocumentService()


# ============================================================
# Public Functions
# ============================================================

async def process_document(
    file: UploadFile,
    user_id: str,
):
    return await document_service.process_document(
        file,
        user_id,
    )


async def delete_document(
    document_id: str,
    user_id: str,
):
    return await document_service.delete_document(
        document_id,
        user_id,
    )
