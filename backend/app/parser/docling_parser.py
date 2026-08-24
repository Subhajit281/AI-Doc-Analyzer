import os
os.environ["TORCHINDUCTOR_DISABLE"] = "1"
os.environ["TORCH_COMPILE_DISABLE"] = "1"

from pathlib import Path

from docling.document_converter import DocumentConverter

from app.validation.models import ValidationResult

from .base import BaseParser
from .exceptions import DocumentParsingError
from .models import ParsedDocument


class DoclingParser(BaseParser):
    """
    Parser implementation using Docling.
    """

    def __init__(self):
        self.converter = DocumentConverter()

    def parse(
        self,
        file_path: Path,
        validation: ValidationResult,
    ) -> ParsedDocument:

        try:
            result = self.converter.convert(file_path)

            return ParsedDocument(
                source=file_path,
                validation=validation,
                markdown=result.document.export_to_markdown(),
                text=result.document.export_to_text(),
                metadata={},
                raw_document=result.document,
                pages=len(result.document.pages)
            )

        except Exception as e:
            raise DocumentParsingError(
                f"Failed to parse document: {e}"
            ) from e