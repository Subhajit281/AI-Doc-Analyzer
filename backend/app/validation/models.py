from pydantic import BaseModel
from .enums import DocumentType


class DetectionResult(BaseModel):
    document_type: DocumentType
    mime_type: str | None = None
    extension: str | None = None
    
class ValidationResult(BaseModel):
    is_valid: bool
    #document_type:DocumentType
    detection: DetectionResult