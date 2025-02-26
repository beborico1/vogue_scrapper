# src/utils/storage/validation_storage_handler.py
"""Validation handling for storage operations."""

from typing import Dict, Any, List

from .completion_storage_handler import CompletionStorageHandler
from .data_validator import DataValidator


class ValidationStorageHandler(CompletionStorageHandler):
    """Handles validation of data before storage operations."""

    def __init__(self, base_dir: str = None, checkpoint_file: str = None):
        """Initialize the validation storage handler.

        Args:
            base_dir: Base directory for storing data files
            checkpoint_file: Optional path to checkpoint file to resume from
        """
        super().__init__(base_dir, checkpoint_file)
        self.validator = DataValidator(self.logger)

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
            self.logger.error("No active designer session")
            return False

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
            self.logger.error("No active designer session")
            return False

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

            # Validate look number
            designer = season["designers"][look_data["designer_index"]]
            if "looks" not in designer:
                designer["looks"] = []
                
            # Check for invalid look number
            if look_data["look_number"] <= 0:
                self.logger.error(f"Invalid look number: {look_data['look_number']}")
                return False

            # Validate image data
            for image in look_data["images"]:
                if not all(key in image for key in ["url", "look_number", "alt_text"]):
                    self.logger.error("Missing required image fields")
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

    def validate_storage_state(self) -> Dict[str, Any]:
        """Perform comprehensive validation of storage state.

        Returns:
            Dict[str, Any]: Validation results
        """
        validation_results = {"valid": True, "checks": [], "errors": []}

        try:
            # Check file integrity
            if not self.validate():
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