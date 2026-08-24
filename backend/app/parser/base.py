from abc import ABC, abstractmethod
from pathlib import Path

from app.validation.models import ValidationResult

from .models import ParsedDocument


class BaseParser(ABC):

    @abstractmethod
    def parse(
        self,
        file_path: Path,
        validation: ValidationResult,
    ) -> ParsedDocument:
        pass