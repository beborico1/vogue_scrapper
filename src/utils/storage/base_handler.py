"""Base storage handler for managing file operations.

This module provides the foundation for storage operations, handling file
initialization, basic JSON operations, and directory management.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from src.utils.storage.utils import (
    generate_filename,
    read_json_file,
    write_json_file,
    ensure_directory_exists
)
from src.exceptions.errors import StorageError, FileOperationError
from src.config.settings import config

class BaseStorageHandler:
    """Base handler for storage operations providing core file management functionality."""
    
    def __init__(self, base_dir: str = config.storage.BASE_DIR, checkpoint_file: str = None):
        """Initialize the base storage handler.
        
        Args:
            base_dir: Base directory for storing data files
            checkpoint_file: Optional path to existing checkpoint file
        
        Raises:
            StorageError: If initialization fails
        """
        try:
            self.base_dir = Path(base_dir)
            ensure_directory_exists(self.base_dir)
            self.current_file = Path(checkpoint_file) if checkpoint_file else None
            self.logger = logging.getLogger(__name__)
            
            if self.current_file:
                if not self.current_file.is_absolute():
                    self.current_file = self.base_dir / self.current_file
                if not self.current_file.exists():
                    self.logger.warning(f"Checkpoint file {self.current_file} not found")
                    
        except Exception as e:
            raise StorageError(f"Error initializing storage handler: {str(e)}")

    def initialize_file(self, initial_data: Optional[Dict[str, Any]] = None) -> Path:
        """Initialize a new JSON file or use existing checkpoint.
        
        Args:
            initial_data: Optional initial data structure
        
        Returns:
            Path to the initialized data file
        
        Raises:
            StorageError: If file initialization fails
        """
        try:
            # If we have a checkpoint file, validate and use it
            if self.current_file:
                if self.current_file.exists():
                    self.logger.info(f"Using existing checkpoint file: {self.current_file}")
                    # Validate file is readable
                    read_json_file(self.current_file)
                    return self.current_file
                else:
                    self.logger.warning(
                        f"Checkpoint file not found: {self.current_file}"
                    )
                    # Don't reset current_file - keep the specified path
            
            # If no checkpoint or checkpoint doesn't exist, generate new filename
            if not self.current_file:
                self.current_file = generate_filename(self.base_dir)
                
            # Create new file with initial data
            data = initial_data or self._get_default_structure()
            write_json_file(self.current_file, data)
            self.logger.info(f"Initialized new data file: {self.current_file}")
            return self.current_file
                
        except Exception as e:
            raise StorageError(f"Error initializing file: {str(e)}")

    def read_data(self) -> Dict[str, Any]:
        """Read the current data file.
        
        Returns:
            Dictionary containing the file data
        
        Raises:
            FileOperationError: If file cannot be read
            StorageError: If no file is initialized
        """
        if not self.current_file:
            raise StorageError("No file initialized. Call initialize_file() first.")
        return read_json_file(self.current_file)

    def write_data(self, data: Dict[str, Any]) -> None:
        """Write data to the current file.
        
        Args:
            data: Data to write to file
        
        Raises:
            FileOperationError: If file cannot be written
            StorageError: If no file is initialized
        """
        if not self.current_file:
            raise StorageError("No file initialized. Call initialize_file() first.")
        write_json_file(self.current_file, data)

    def _get_default_structure(self) -> Dict[str, Any]:
        """Get the default data structure for new files.
        
        Returns:
            Dictionary containing the default data structure
        """
        return {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "overall_progress": {
                    "total_seasons": 0,
                    "completed_seasons": 0,
                    "total_designers": 0,
                    "completed_designers": 0,
                    "total_looks": 0,
                    "extracted_looks": 0
                }
            },
            "seasons": []
        }

    def get_current_file(self) -> Optional[Path]:
        """Get the path to the current data file.
        
        Returns:
            Path to current file or None if no file initialized
        """
        return self.current_file

    def validate_file(self) -> bool:
        """Validate that the current file exists and is readable.
        
        Returns:
            True if file exists and is readable
        
        Raises:
            FileOperationError: If file validation fails
        """
        if not self.current_file:
            return False
            
        try:
            read_json_file(self.current_file)
            return True
        except FileOperationError:
            return False
            
    def exists(self) -> bool:
        """Check if the current file exists.
        
        Returns:
            True if file exists
        """
        return self.current_file is not None and self.current_file.exists()