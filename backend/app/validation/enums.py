from enum import Enum

class DocumentType(str,Enum):
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"
    CSV = "csv"
    HTML = "html"
    MARKDOWN = "md"
    TXT = "txt"

    UNKNOWN = "unknown"
