import os
os.environ["TORCHINDUCTOR_DISABLE"] = "1"
os.environ["TORCH_COMPILE_DISABLE"] = "1"
os.environ.setdefault("OMP_NUM_THREADS", "1")

import threading
from pathlib import Path

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat

from app.validation.models import ValidationResult
from .base import BaseParser
from .exceptions import DocumentParsingError
from .models import ParsedDocument


def _build_lightweight_converter() -> DocumentConverter:
    """
    Default DocumentConverter() loads OCR + table-structure models —
    the single biggest memory cost in this app. Most uploads are
    text-based PDFs, so turn both off unless you specifically need
    scanned-document support.
    """
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False
    pipeline_options.do_table_structure = False
    pipeline_options.generate_page_images = False
    pipeline_options.generate_picture_images = False

    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )


class DoclingParser(BaseParser):
    """Process-wide singleton — same reasoning as DocumentEmbedder."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance.converter = _build_lightweight_converter()
                    cls._instance = instance
        return cls._instance

    def parse(self, file_path: Path, validation: ValidationResult) -> ParsedDocument:
        try:
            result = self.converter.convert(file_path)
            return ParsedDocument(
                source=file_path,
                validation=validation,
                markdown=result.document.export_to_markdown(),
                text=result.document.export_to_text(),
                metadata={},
                raw_document=result.document,
                pages=len(result.document.pages),
            )
        except Exception as e:
            raise DocumentParsingError(f"Failed to parse document: {e}") from e