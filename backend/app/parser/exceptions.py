class ParserError(Exception):
    """Base parser exception."""
    pass


class DocumentParsingError(ParserError):
    """Raised when parsing fails."""
    pass