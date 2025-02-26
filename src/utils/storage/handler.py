# src/utils/storage/handler.py
"""Enhanced storage handler with validation and safety checks.

This file provides backward compatibility for imports after code refactoring.
It simply re-exports DataStorageHandler from the new module structure.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Import the new implementation
from .data_storage_handler import DataStorageHandler

# Re-export for backward compatibility
__all__ = ['DataStorageHandler']