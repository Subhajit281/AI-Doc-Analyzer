from pathlib import Path

from .detector import DocumentDetector
from .enums import DocumentType
from .exceptions import (
    EmptyDocumentError,
    UnsupportedDocumentError,
)
from .models import ValidationResult


class DocumentValidator:
    """
    Validates uploaded documents before they enter the parsing pipeline.
    """

    def __init__(self):
        self.detector = DocumentDetector()

    def validate(self, file_path: Path) -> ValidationResult:
        """
        Validate a document using the configured validation rules.
        """

        # File must exist
        if not file_path.exists():
            raise FileNotFoundError(f"{file_path} does not exist.")

        # File must not be empty
        if file_path.stat().st_size == 0:
            raise EmptyDocumentError("Uploaded document is empty.")

        # Detect document type
        detection = self.detector.detect(file_path)

        # Document type must be supported
        if detection.document_type == DocumentType.UNKNOWN:
            raise UnsupportedDocumentError(
                "Unsupported or unrecognized document type."
            )

        return ValidationResult(
            is_valid=True,
            detection=detection,
        )