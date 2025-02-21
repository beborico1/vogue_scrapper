# utils/storage/storage_handler.py
"""Enhanced storage handler with validation, session management, and safety checks.

This module provides a robust implementation of the storage handler with:
- Strong data validation
- Session-based processing
- Atomic updates
- Error recovery
- Comprehensive logging
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib
import json
from pathlib import Path

from .data_updater import DataUpdater
from .data_validator import DataValidator
from ...exceptions.errors import StorageError, ValidationError


class DataStorageHandler(DataUpdater):
    """Enhanced storage handler with validation and safety checks."""

    def __init__(self, base_dir: str = None, checkpoint_file: str = None):
        """Initialize the storage handler with validation capabilities.

        Args:
            base_dir: Base directory for storing data files
            checkpoint_file: Optional path to checkpoint file to resume from
        """
        super().__init__(base_dir, checkpoint_file)
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

    def _start_designer_session(self, designer_url: str) -> None:
        """Start a new designer processing session.

        Args:
            designer_url: URL identifier of the designer

        Raises:
            StorageError: If another session is already active
        """
        if self._active_session:
            raise StorageError("Another designer session is already active")

        self._active_session = {
            "designer_url": designer_url,
            "start_time": datetime.now().isoformat(),
            "operations": [],
            "state_hash": self._calculate_state_hash(),
        }

        self.logger.info(f"Started session for designer: {designer_url}")

    def _end_designer_session(self) -> None:
        """End current designer processing session safely."""
        if self._active_session:
            end_time = datetime.now().isoformat()

            # Log session completion
            self._transaction_log.append(
                {
                    "type": "session",
                    "designer_url": self._active_session["designer_url"],
                    "start_time": self._active_session["start_time"],
                    "end_time": end_time,
                    "operations_count": len(self._active_session["operations"]),
                    "final_state_hash": self._calculate_state_hash(),
                }
            )

            self._active_session = None
            self.save_progress()
            self.logger.info("Designer session ended successfully")

    def update_data(
        self,
        season_data: Optional[Dict[str, Any]] = None,
        designer_data: Optional[Dict[str, Any]] = None,
        look_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update storage with new data using enhanced validation.

        Args:
            season_data: Optional season data to update
            designer_data: Optional designer data to update
            look_data: Optional look data to update

        Returns:
            bool: True if update successful
        """
        try:
            # Create restore point before update
            self._create_restore_point()

            if season_data:
                success = self._update_season_with_validation(season_data)
            elif designer_data:
                success = self._update_designer_with_validation(designer_data)
            elif look_data:
                success = self._update_look_with_validation(look_data)
            else:
                raise ValidationError("No valid data provided for update")

            if success:
                self._log_successful_update()
                return True
            else:
                self._restore_from_last_point()
                return False

        except Exception as e:
            self.logger.error(f"Error in update_data: {str(e)}")
            self._restore_from_last_point()
            raise StorageError(f"Update failed: {str(e)}")

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
                        if self._is_designer_fully_completed(designer)
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

    def _update_look_with_validation(self, look_data: Dict[str, Any]) -> bool:
        """Update look data with validation checks.

        Args:
            look_data: Look data to update

        Returns:
            bool: True if update successful
        """
        if not self._active_session:
            raise StorageError("No active designer session")

        try:
            current_data = self.read_data()

            # Validate look data
            if not self._validate_look_assignment(
                current_data,
                look_data["season_index"],
                look_data["designer_index"],
                look_data["look_number"],
                look_data["images"],
            ):
                return False

            success = super().update_look_data(
                look_data["season_index"],
                look_data["designer_index"],
                look_data["look_number"],
                look_data["images"],
            )

            if success:
                self._active_session["operations"].append(
                    {
                        "type": "look_update",
                        "look_number": look_data["look_number"],
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            return success

        except Exception as e:
            self.logger.error(f"Error updating look data: {str(e)}")
            return False

    def _validate_look_assignment(
        self,
        data: Dict[str, Any],
        season_index: int,
        designer_index: int,
        look_number: int,
        images: List[Dict[str, str]],
    ) -> bool:
        """Validate look assignment data.

        Args:
            data: Current storage data
            season_index: Season index
            designer_index: Designer index
            look_number: Look number
            images: Image data list

        Returns:
            bool: True if validation passes
        """
        try:
            if season_index >= len(data["seasons"]):
                self.logger.error(f"Invalid season index: {season_index}")
                return False

            season = data["seasons"][season_index]
            if designer_index >= len(season["designers"]):
                self.logger.error(f"Invalid designer index: {designer_index}")
                return False

            designer = season["designers"][designer_index]
            if "looks" not in designer:
                designer["looks"] = []

            # Validate look number
            if look_number <= 0 or look_number > designer.get("total_looks", float("inf")):
                self.logger.error(f"Invalid look number: {look_number}")
                return False

            # Validate image data
            for image in images:
                if not all(key in image for key in ["url", "look_number", "alt_text"]):
                    self.logger.error("Missing required image fields")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating look assignment: {str(e)}")
            return False

    def _create_restore_point(self) -> None:
        """Create a restore point for the current state."""
        try:
            current_data = self.read_data()
            checkpoint_hash = self._calculate_state_hash()
            self._checkpoints[checkpoint_hash] = json.dumps(current_data)

            # Keep only last 5 restore points
            if len(self._checkpoints) > 5:
                oldest_hash = list(self._checkpoints.keys())[0]
                del self._checkpoints[oldest_hash]

        except Exception as e:
            self.logger.error(f"Error creating restore point: {str(e)}")

    def _restore_from_last_point(self) -> bool:
        """Restore data from the last restore point."""
        try:
            if not self._checkpoints:
                return False

            latest_hash = list(self._checkpoints.keys())[-1]
            checkpoint_data = json.loads(self._checkpoints[latest_hash])

            self.write_data(checkpoint_data)
            self.logger.info("Successfully restored from last checkpoint")
            return True

        except Exception as e:
            self.logger.error(f"Error restoring from checkpoint: {str(e)}")
            return False

    def _calculate_state_hash(self) -> str:
        """Calculate hash of current state for integrity checking."""
        try:
            current_data = self.read_data()
            data_str = json.dumps(current_data, sort_keys=True)
            return hashlib.md5(data_str.encode()).hexdigest()
        except Exception as e:
            self.logger.error(f"Error calculating state hash: {str(e)}")
            return ""

    def _log_successful_update(self) -> None:
        """Log successful data update operation."""
        if self._active_session:
            self._active_session["operations"].append(
                {
                    "type": "successful_update",
                    "timestamp": datetime.now().isoformat(),
                    "state_hash": self._calculate_state_hash(),
                }
            )

    def get_operation_log(self) -> List[Dict[str, Any]]:
        """Get log of all storage operations.

        Returns:
            List[Dict[str, Any]]: List of operation records
        """
        return self.validator.get_operation_log()

    def analyze_operations(self) -> Dict[str, Any]:
        """Analyze storage operations for potential issues.

        Returns:
            Dict[str, Any]: Analysis results
        """
        return self.validator.analyze_storage_operations()

    def get_active_session_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current active session.

        Returns:
            Optional[Dict[str, Any]]: Active session info or None
        """
        if self._active_session:
            return {
                "designer_url": self._active_session["designer_url"],
                "start_time": self._active_session["start_time"],
                "operation_count": len(self._active_session["operations"]),
                "current_state_hash": self._calculate_state_hash(),
            }
        return None

    def validate_storage_state(self) -> Dict[str, Any]:
        """Perform comprehensive validation of storage state.

        Returns:
            Dict[str, Any]: Validation results
        """
        validation_results = {"valid": True, "checks": [], "errors": []}

        try:
            # Check file integrity
            if not self.validate_file():
                validation_results["valid"] = False
                validation_results["errors"].append("File integrity check failed")

            # Validate data structure
            current_data = self.read_data()
            if not self.validator.validate_data_structure(current_data):
                validation_results["valid"] = False
                validation_results["errors"].append("Data structure validation failed")

            # Check session state
            if self._active_session:
                validation_results["checks"].append(
                    {
                        "type": "active_session",
                        "designer_url": self._active_session["designer_url"],
                        "operation_count": len(self._active_session["operations"]),
                    }
                )

            # Validate checkpoints
            validation_results["checks"].append(
                {
                    "type": "checkpoints",
                    "count": len(self._checkpoints),
                    "latest_hash": (
                        list(self._checkpoints.keys())[-1] if self._checkpoints else None
                    ),
                }
            )

            return validation_results

        except Exception as e:
            self.logger.error(f"Error validating storage state: {str(e)}")
            return {"valid": False, "errors": [str(e)]}

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

    def _update_season_with_validation(self, season_data: Dict[str, Any]) -> bool:
        """Update season data with validation checks.

        Args:
            season_data: Season data to update

        Returns:
            bool: True if update successful
        """
        # Validate season data structure
        if not all(key in season_data for key in ["season", "year", "url"]):
            self.logger.error("Missing required season fields")
            return False

        # Check for duplicate seasons
        if self._check_duplicate_season(season_data):
            self.logger.warning("Duplicate season detected, updating existing")

        return super().update_season_data(season_data)

    def _update_designer_with_validation(self, designer_data: Dict[str, Any]) -> bool:
        """Update designer data with validation checks.

        Args:
            designer_data: Designer data to update

        Returns:
            bool: True if update successful
        """
        if not self._active_session:
            raise StorageError("No active designer session")

        try:
            current_data = self.read_data()

            # Validate required fields
            if not all(key in designer_data for key in ["data", "season_index", "designer_index"]):
                self.logger.error("Missing required designer fields")
                return False

            # Ensure seasons array exists
            if "seasons" not in current_data:
                current_data["seasons"] = []

            # Validate indices
            if designer_data["season_index"] >= len(current_data["seasons"]):
                self.logger.error(f"Invalid season index: {designer_data['season_index']}")
                return False

            season = current_data["seasons"][designer_data["season_index"]]
            if "designers" not in season:
                season["designers"] = []

            return super().update_designer_data(
                designer_data["season_index"],
                designer_data["data"],
                designer_data.get("total_looks", 0),
            )

        except Exception as e:
            self.logger.error(f"Error in designer update validation: {str(e)}")
            return False

    def _update_look_with_validation(self, look_data: Dict[str, Any]) -> bool:
        """Update look data with validation checks.

        Args:
            look_data: Look data to update

        Returns:
            bool: True if update successful
        """
        if not self._active_session:
            raise StorageError("No active designer session")

        try:
            current_data = self.read_data()

            # Validate required fields
            if not all(
                key in look_data
                for key in ["season_index", "designer_index", "look_number", "images"]
            ):
                self.logger.error("Missing required look fields")
                return False

            # Validate indices
            if look_data["season_index"] >= len(current_data["seasons"]):
                self.logger.error(f"Invalid season index: {look_data['season_index']}")
                return False

            season = current_data["seasons"][look_data["season_index"]]
            if look_data["designer_index"] >= len(season["designers"]):
                self.logger.error(f"Invalid designer index: {look_data['designer_index']}")
                return False

            return super().update_look_data(
                look_data["season_index"],
                look_data["designer_index"],
                look_data["look_number"],
                look_data["images"],
            )

        except Exception as e:
            self.logger.error(f"Error in look update validation: {str(e)}")
            return False

    def _check_duplicate_season(self, season_data: Dict[str, Any]) -> bool:
        """Check if season already exists in storage.

        Args:
            season_data: Season data to check

        Returns:
            bool: True if season exists
        """
        try:
            current_data = self.read_data()
            for season in current_data.get("seasons", []):
                if (
                    season["season"] == season_data["season"]
                    and season["year"] == season_data["year"]
                ):
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Error checking for duplicate season: {str(e)}")
            return False
