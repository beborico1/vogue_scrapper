from .handler import DataStorageHandler
# src/utils/storage/__init__.py
"""Storage module for Vogue Runway scraper.

This module provides functionality for storing and retrieving runway data
with robust error handling, validation, and session management.
"""

from .data_storage_handler import DataStorageHandler

__all__ = ["DataStorageHandler"]