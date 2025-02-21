# src/utils/storage/handler.py
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import json

"""Enhanced storage handler with validation and safety checks."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import json

from src.utils.storage.data_updater import DataUpdater
from src.utils.storage.data_validator import DataValidator
from src.exceptions.errors import StorageError, ValidationError


class DataStorageHandler(DataUpdater):
    """Enhanced storage handler with validation and safety checks."""

    # Rest of the class implementation remains the same

    def __init__(self, base_dir: str = None, checkpoint_file: str = None):
        """Initialize the storage handler with validation capabilities.

        Args:
            base_dir: Base directory for storing data files
            checkpoint_file: Optional path to checkpoint file to resume from
        """
        # Initialize logger first
        self.logger = logging.getLogger(__name__)

        # Initialize parent class
        super().__init__(base_dir, checkpoint_file)

        # Initialize components
        self.validator = DataValidator(self.logger)
        self._active_session = None
        self._transaction_log = []
        self._checkpoints = {}

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
        """Initialize storage file with proper structure."""
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
            if self.logger:  # Check if logger exists before using
                self.logger.error(f"Error initializing file: {str(e)}")
            raise StorageError(f"File initialization failed: {str(e)}")

    def validate(self) -> Dict[str, Any]:
        """Validate current storage state."""
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
        """Get current scraping status and progress."""
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

    def is_season_completed(self, season: Dict[str, str]) -> bool:
        """Check if a season has been completely processed.

        Args:
            season: Season data containing season name and year

        Returns:
            bool: True if season is completed
        """
        try:
            if not self.current_file:
                return False

            current_data = self.read_data()
            season_name = season["season"]
            season_year = season["year"]

            # Find matching season in storage
            for stored_season in current_data["seasons"]:
                if stored_season["season"] == season_name and stored_season["year"] == season_year:

                    # Must have designers and total_designers set
                    if (
                        not stored_season.get("designers")
                        or stored_season.get("total_designers", 0) == 0
                    ):
                        return False

                    total_designers = stored_season.get("total_designers", 0)
                    completed_designers = sum(
                        1
                        for designer in stored_season["designers"]
                        if self.is_designer_completed(designer["url"])
                    )

                    # All designers must be completed
                    return completed_designers >= total_designers

            return False

        except Exception as e:
            self.logger.error(f"Error checking season completion: {str(e)}")
            return False

    def is_designer_completed(self, designer_url: str) -> bool:
        """Check if a designer's show has been completely processed.

        Args:
            designer_url: URL identifier of the designer

        Returns:
            bool: True if designer is completed
        """
        try:
            if not self.current_file:
                return False

            current_data = self.read_data()

            # Search through all seasons and designers
            for season in current_data["seasons"]:
                for designer in season.get("designers", []):
                    if designer["url"] == designer_url:
                        return self._is_designer_fully_completed(designer)

            return False

        except Exception as e:
            self.logger.error(f"Error checking designer completion: {str(e)}")
            return False

    def _is_designer_fully_completed(self, designer: Dict[str, Any]) -> bool:
        """Helper method to check if a designer is fully completed.

        Args:
            designer: Designer data dictionary

        Returns:
            bool: True if designer is fully completed
        """
        try:
            # Must have looks and total_looks set
            if not designer.get("looks") or designer.get("total_looks", 0) == 0:
                return False

            total_looks = designer.get("total_looks", 0)
            completed_looks = sum(
                1 for look in designer["looks"] if self._is_look_fully_completed(look)
            )

            # All looks must be completed and have images
            is_completed = completed_looks >= total_looks

            # Update designer completion status
            designer["completed"] = is_completed
            return is_completed

        except Exception as e:
            self.logger.error(f"Error checking designer completion status: {str(e)}")
            return False

    def _is_look_fully_completed(self, look: Dict[str, Any]) -> bool:
        """Helper method to check if a look is fully completed.

        Args:
            look: Look data dictionary

        Returns:
            bool: True if look is fully completed
        """
        try:
            # Check if look has images and all required fields
            return bool(look.get("images")) and all(
                required_key in image
                for image in look["images"]
                for required_key in ["url", "look_number", "type", "timestamp"]
            )
        except Exception as e:
            self.logger.error(f"Error checking look completion status: {str(e)}")
            return False

    def _update_completion_status(self, designer: Dict[str, Any], season: Dict[str, Any]) -> None:
        """Update completion status for designer and season.

        Args:
            designer: Designer data dictionary
            season: Season data dictionary
        """
        try:
            # Update designer completion
            designer_completed = self._is_designer_fully_completed(designer)
            designer["completed"] = designer_completed

            # Update season completion if all designers are completed
            if designer_completed:
                season_completed = all(
                    self._is_designer_fully_completed(d) for d in season.get("designers", [])
                )
                season["completed"] = season_completed

        except Exception as e:
            self.logger.error(f"Error updating completion status: {str(e)}")
