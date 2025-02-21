# utils/storage/errors.py
class StorageError(Exception):
    """Base exception for storage-related errors."""

    pass


class ValidationError(Exception):
    """Exception for data validation errors."""

    pass
