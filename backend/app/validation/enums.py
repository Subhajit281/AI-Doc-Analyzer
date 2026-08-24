from enum import Enum

class DocumentType(str,Enum):
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"
    HTML = "html"
    MARKDOWN = "md"
    TXT = "txt"

    UNKNOWN = "unknown"