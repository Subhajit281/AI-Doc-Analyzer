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
    "txt": DocumentType.TXT,
}

class DocumentDetector:
    """ Detect the actual document type using magic bytes"""

    def detect(self,file_path:Path) -> DetectionResult:

        if not file_path.exists():
            raise FileNotFoundError(
            f"{file_path} does not exist."
        )

        detected_file = filetype.guess(file_path)

        if detected_file is None:
            return DetectionResult(
                document_type=DocumentType.UNKNOWN,
                mime_type=None,
                extension=None,
            )
        return DetectionResult(
            document_type=_DOCUMENT_TYPE_MAP.get(
                detected_file.extension,
                DocumentType.UNKNOWN,
            ),
            mime_type=detected_file.mime,
            extension=detected_file.extension,
        )