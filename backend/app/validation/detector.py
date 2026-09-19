from pathlib import Path

import filetype

from .enums import DocumentType
from .models import DetectionResult


_DOCUMENT_TYPE_MAP = {
    "pdf": DocumentType.PDF,
    "docx": DocumentType.DOCX,
    "pptx": DocumentType.PPTX,
    "xlsx": DocumentType.XLSX,
    "html": DocumentType.HTML,
    "htm": DocumentType.HTML,
    "md": DocumentType.MARKDOWN,
    "markdown": DocumentType.MARKDOWN,
    "txt": DocumentType.TXT,
}


_MIME_TYPE_MAP = {
    "application/pdf": DocumentType.PDF,

    "text/plain": DocumentType.TXT,

    "text/html": DocumentType.HTML,

    "text/markdown": DocumentType.MARKDOWN,

    "application/vnd.openxmlformats-officedocument"
    ".wordprocessingml.document": DocumentType.DOCX,

    "application/vnd.openxmlformats-officedocument"
    ".presentationml.presentation": DocumentType.PPTX,

    "application/vnd.openxmlformats-officedocument"
    ".spreadsheetml.sheet": DocumentType.XLSX,
}


class DocumentDetector:
    """
    Detect document type using content signatures with
    extension fallback for text-based formats.
    """

    def detect(
        self,
        file_path: Path
    ) -> DetectionResult:

        if not file_path.exists():
            raise FileNotFoundError(
                f"{file_path} does not exist."
            )

        # =====================================================
        # 1. Try content / magic-byte detection
        # =====================================================

        detected_file = filetype.guess(file_path)

        if detected_file is not None:

            extension = detected_file.extension.lower()
            mime_type = detected_file.mime

            document_type = _DOCUMENT_TYPE_MAP.get(
                extension
            )

            if document_type is None:

                document_type = _MIME_TYPE_MAP.get(
                    mime_type,
                    DocumentType.UNKNOWN
                )

            return DetectionResult(
                document_type=document_type,
                mime_type=mime_type,
                extension=extension,
            )

        # =====================================================
        # 2. Fallback to file extension
        #
        # Plain-text formats usually have no magic signature.
        # =====================================================

        extension = file_path.suffix.lower().lstrip(".")

        document_type = _DOCUMENT_TYPE_MAP.get(
            extension,
            DocumentType.UNKNOWN,
        )

        mime_type = self._get_text_mime_type(
            document_type
        )

        return DetectionResult(
            document_type=document_type,
            mime_type=mime_type,
            extension=extension or None,
        )

    # =========================================================
    # Text MIME fallback
    # =========================================================

    def _get_text_mime_type(
        self,
        document_type: DocumentType
    ) -> str | None:

        if document_type == DocumentType.TXT:
            return "text/plain"

        if document_type == DocumentType.MARKDOWN:
            return "text/markdown"

        if document_type == DocumentType.HTML:
            return "text/html"

        return None