# src/exceptions/errors.py

"""Custom exceptions for the Vogue Runway scraper.

This module defines all custom exceptions used throughout the scraper
implementation. It provides a hierarchy of exceptions to handle different
types of errors that may occur during the scraping process.
"""

class ScraperError(Exception):
    """Base exception for all scraper-related errors."""
    pass

class AuthenticationError(ScraperError):
    """
    Raised when authentication fails.
    
    This could be due to:
    - Invalid credentials
    - Failed login attempts
    - Session expiration
    - Authentication endpoint issues
    """
    pass

class ElementNotFoundError(ScraperError):
    """
    Raised when an expected element is not found in the page.
    
    This could be due to:
    - Page structure changes
    - Loading issues
    - Invalid selectors
    - Timing issues
    """
    pass

class NavigationError(ScraperError):
    """
    Raised when navigation to a page fails.
    
    This could be due to:
    - Invalid URLs
    - Network issues
    - Page timeouts
    - Redirects failing
    """
    pass

class DataExtractionError(ScraperError):
    """
    Raised when data cannot be extracted from a page element.
    
    This could be due to:
    - Unexpected data format
    - Missing attributes
    - Changed page structure
    - Partial page loads
    """
    pass

class StorageError(ScraperError):
    """
    Raised when storage operations fail.
    
    This could be due to:
    - File system permissions
    - Disk space issues
    - Invalid file paths
    - Data serialization errors
    """
    pass

class ValidationError(ScraperError):
    """
    Raised when data validation fails.
    
    This could be due to:
    - Invalid data format
    - Missing required fields
    - Data type mismatches
    - Range/constraint violations
    """
    pass

class FileOperationError(StorageError):
    """
    Raised when file operations fail.
    
    This could be due to:
    - File not found
    - Permission denied
    - Invalid file format
    - I/O errors
    """
    pass

# Backwards compatibility aliases
ScraperException = ScraperError  # For backwards compatibility
DataSaveError = StorageError  # For backwards compatibility