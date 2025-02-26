# src/utils/storage/base_storage_handler.py
"""Base storage handler with core functionality for file operations."""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .data_updater import DataUpdater
from ...exceptions.errors import StorageError


class BaseStorageHandler(DataUpdater):
    """Base storage handler with core file operations functionality."""

    def __init__(self, base_dir: str = None, checkpoint_file: str = None):
        """Initialize the base storage handler.

        Args:
            base_dir: Base directory for storing data files
            checkpoint_file: Optional path to checkpoint file to resume from
        """
        # Initialize logger first
        self.logger = logging.getLogger(__name__)

        # Initialize parent class
        super().__init__(base_dir, checkpoint_file)

        # Set up base directory
        self.base_dir = Path(base_dir) if base_dir else Path("data")
        self.base_dir.mkdir(exist_ok=True)

        # Initialize or load checkpoint
        if checkpoint_file:
            self.current_file = Path(checkpoint_file)
        else:
            # Generate new filename with timestamp if no checkpoint
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_file = self.base_dir / f"vogue_data_{timestamp}.json"

    def initialize_file(self) -> Path:
        """Initialize storage file with proper structure.

        Returns:
            Path: Path to initialized file
        """
        try:
            if self.current_file.exists():
                self.logger.info(f"Using existing file: {self.current_file}")
                return self.current_file

            # Create new file with initial structure
            initial_data = {
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

            # Ensure directory exists
            self.current_file.parent.mkdir(exist_ok=True)

            # Write initial data
            with open(self.current_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=2)

            self.logger.info(f"Initialized new file: {self.current_file}")
            return self.current_file

        except Exception as e:
            self.logger.error(f"Error initializing file: {str(e)}")
            raise StorageError(f"File initialization failed: {str(e)}")

    def validate(self) -> Dict[str, Any]:
        """Validate current storage state.

        Returns:
            Dict[str, Any]: Validation status and any error messages
        """
        try:
            if not self.current_file:
                return {"valid": False, "error": "No file initialized"}

            current_data = self.read_data()
            required_keys = ["metadata", "seasons"]
            metadata_keys = ["created_at", "last_updated", "overall_progress"]

            # Check basic structure
            if not all(key in current_data for key in required_keys):
                return {"valid": False, "error": "Missing required top-level keys"}

            if not all(key in current_data["metadata"] for key in metadata_keys):
                return {"valid": False, "error": "Invalid metadata structure"}

            # Validate season data
            for season in current_data["seasons"]:
                if not all(key in season for key in ["season", "year", "url", "designers"]):
                    return {"valid": False, "error": "Invalid season structure"}

            return {"valid": True}

        except Exception as e:
            self.logger.error(f"Validation error: {str(e)}")
            return {"valid": False, "error": f"Validation failed: {str(e)}"}

    def get_status(self) -> Dict[str, Any]:
        """Get current scraping status and progress.

        Returns:
            Dict[str, Any]: Current status information
        """
        try:
            current_data = self.read_data()
            progress = current_data["metadata"]["overall_progress"]

            return {
                "total_seasons": progress["total_seasons"],
                "completed_seasons": progress["completed_seasons"],
                "total_designers": progress["total_designers"],
                "completed_designers": progress["completed_designers"],
                "total_looks": progress["total_looks"],
                "extracted_looks": progress["extracted_looks"],
                "current_file": str(self.current_file),
            }
        except Exception as e:
            self.logger.error(f"Error getting status: {str(e)}")
            return {}

    def save_progress(self) -> None:
        """Save current progress to disk."""
        try:
            # Get current data
            current_data = self.read_data()

            # Update last_updated timestamp
            current_data["metadata"]["last_updated"] = datetime.now().isoformat()

            # Write updated data
            self.write_data(current_data)
            self.logger.info("Progress saved successfully")

        except Exception as e:
            self.logger.error(f"Error saving progress: {str(e)}")
            raise StorageError(f"Failed to save progress: {str(e)}")

    def read_data(self) -> Dict[str, Any]:
        """Read data from storage file."""
        try:
            with open(self.current_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to read data: {str(e)}")
            raise StorageError(f"Failed to read data: {str(e)}")

    def write_data(self, data: Dict[str, Any]) -> None:
        """Write data to storage file."""
        try:
            with open(self.current_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to write data: {str(e)}")
            raise StorageError(f"Failed to write data: {str(e)}")