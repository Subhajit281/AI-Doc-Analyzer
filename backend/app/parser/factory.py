import os
from .base import BaseParser
from .lightweight_parser import LightweightParser


def get_document_parser() -> BaseParser:
    """
    Factory to return the appropriate parser backend based on environment configuration.
    
    Defaults to 'lightweight' for smooth execution under 512 MB memory allowance.
    If 'PARSER_BACKEND=docling' is explicitly set, lazily imports DoclingParser.
    """
    backend = os.getenv("PARSER_BACKEND", "lightweight").strip().lower()

    if backend == "docling":
        print("[PARSER] Using DoclingParser backend (high memory requirement).")
        from .docling_parser import DoclingParser
        return DoclingParser()

    print("[PARSER] Using LightweightParser backend (< 30 MB RAM).")
    return LightweightParser()

