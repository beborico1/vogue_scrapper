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

        Raises:
            StorageError: If update fails
            ValidationError: If data validation fails
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

    def _update_season_with_validation(self, season_data: Dict[str, Any]) -> bool:
        """Update season data with validation checks.

        Args:
            season_data: Season data to update

        Returns:
            bool: True if update successful
        """
        # Validate season data structure
        if not self.validator.validate_season_data(season_data):
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

        # Validate designer context
        if not self.validator.validate_designer_context(
            self.read_data(),
            designer_data["season_index"],
            designer_data["designer_index"],
            self._active_session["designer_url"],
        ):
            return False

        return super().update_designer_data(
            designer_data["season_index"], designer_data["data"], designer_data["total_looks"]
        )

    def _update_look_with_validation(self, look_data: Dict[str, Any]) -> bool:
        """Update look data with validation checks.

        Args:
            look_data: Look data to update

        Returns:
            bool: True if update successful
        """
        if not self._active_session:
            raise StorageError("No active designer session")

        # Validate look data
        if not self.validator.validate_look_assignment(
            self.read_data(),
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
        """Restore data from the last restore point.

        Returns:
            bool: True if restore successful
        """
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

    def _check_duplicate_season(self, season_data: Dict[str, Any]) -> bool:
        """Check if season already exists in storage.

        Args:
            season_data: Season data to check

        Returns:
            bool: True if season exists
        """
        try:
            current_data = self.read_data()
            for season in current_data["seasons"]:
                if (
                    season["season"] == season_data["season"]
                    and season["year"] == season_data["year"]
                ):
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Error checking for duplicate season: {str(e)}")
            return False

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

    def validate(self) -> Dict[str, Any]:
        """Validate current storage state.

        Returns:
            Dict containing validation status and any error messages
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
