# utils/storage/base_handler.py
"""Base storage handler for managing file operations.

This module provides the foundation for storage operations, handling file
initialization, basic JSON operations, and directory management.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from src.utils.storage.utils import (
    generate_filename,
    read_json_file,
    write_json_file,
    ensure_directory_exists,
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
            self.base_dir = Path(base_dir or "data")
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

    def read_data(self) -> Dict[str, Any]:
        """Read the current data file.

        Returns:
            Dictionary containing the file data with seasons sorted chronologically

        Raises:
            FileOperationError: If file cannot be read
            StorageError: If no file is initialized
        """
        if not self.current_file:
            raise StorageError("No file initialized. Call initialize_file() first.")
            
        data = read_json_file(self.current_file)
        
        # Sort seasons chronologically if they exist
        if "seasons" in data and isinstance(data["seasons"], list):
            data["seasons"] = self._sort_seasons_chronologically(data["seasons"])
            
        return data
        
    def _sort_seasons_chronologically(self, seasons: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort seasons chronologically by year and season.
        
        Args:
            seasons: List of season dictionaries
            
        Returns:
            List of sorted season dictionaries
        """
        from src.config.settings import config
        
        def season_sort_key(season):
            # Helper function to convert season name to a numeric value for sorting
            season_order = {
                "spring": 0,
                "summer": 1,
                "fall": 2, 
                "autumn": 2,  # Treat 'autumn' same as 'fall'
                "winter": 3,
                "resort": 4,
                "pre-fall": 5,
                "pre-spring": 6,
                "couture": 7
            }
            
            season_name = season.get("season", "").lower()
            year = season.get("year", "0")
            
            # Extract season from complex names (e.g., "Fall Ready-to-Wear" -> "fall")
            for key in season_order.keys():
                if key in season_name:
                    season_name = key
                    break
            
            # Get the numeric order or default to 99 (end of sort)
            season_num = season_order.get(season_name, 99)
            
            # Return a tuple of (year, season_number) for sorting
            return (int(year) if year.isdigit() else 0, season_num)
        
        # Sort seasons based on config sorting_type (ascending or descending)
        sorted_seasons = sorted(seasons, key=season_sort_key, reverse=(config.sorting_type.lower() == "desc"))
        return sorted_seasons

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
                    "extracted_looks": 0,
                },
            },
            "seasons": [],
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