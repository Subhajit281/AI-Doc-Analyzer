from pathlib import Path
from pydantic import BaseModel, ConfigDict
from app.validation.models import ValidationResult


class ParsedDocument(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    source: Path
    validation: ValidationResult

    markdown: str
    text: str

    pages: int
    metadata: dict

    raw_document: object