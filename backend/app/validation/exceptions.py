class ValidationError(Exception):
    """
    Base exception for all document validation errors.
    """
    pass


class UnsupportedDocumentError(ValidationError):
    """
    Raised when the uploaded document type is not supported.
    """
    pass


class EmptyDocumentError(ValidationError):
    """
    Raised when the uploaded document is empty.
    """
    pass


class CorruptedDocumentError(ValidationError):
    """
    Raised when the uploaded document cannot be read or is corrupted.
    """
    pass


class FileTooLargeError(ValidationError):
    """
    Raised when the uploaded document exceeds the maximum allowed size.
    """
    pass