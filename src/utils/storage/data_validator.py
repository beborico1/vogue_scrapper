"""Data validation and debugging module for storage operations."""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime


class DataValidator:
    """Validates data consistency and tracks storage operations."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.operation_log = []

    def validate_designer_context(
        self, data: Dict[str, Any], season_index: int, designer_index: int, designer_url: str
    ) -> bool:
        """Validate that indices point to correct designer."""
        try:
            # Check if seasons array exists and has enough elements
            if not data.get("seasons") or season_index >= len(data["seasons"]):
                self.logger.error(f"Invalid season index: {season_index}")
                return False

            season = data["seasons"][season_index]

            # Initialize designers array if it doesn't exist
            if "designers" not in season:
                season["designers"] = []

            # If this is a new designer being added
            if designer_index >= len(season["designers"]):
                # Allow new designer to be added at next index
                if designer_index == len(season["designers"]):
                    self._log_operation(
                        "validate_context",
                        {
                            "season_index": season_index,
                            "designer_index": designer_index,
                            "designer_url": designer_url,
                            "timestamp": datetime.now().isoformat(),
                            "note": "New designer initialization",
                        },
                    )
                    return True
                else:
                    self.logger.error(f"Designer index {designer_index} out of range")
                    return False

            # For existing designer, verify URL match
            designer = season["designers"][designer_index]
            if designer["url"] != designer_url:
                self.logger.error(
                    f"Designer mismatch: Expected {designer_url}, "
                    f"found {designer['url']} at indices [{season_index}, {designer_index}]"
                )
                return False

            self._log_operation(
                "validate_context",
                {
                    "season_index": season_index,
                    "designer_index": designer_index,
                    "designer_url": designer_url,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            return True

        except Exception as e:
            self.logger.error(f"Validation error: {str(e)}")
            return False

    def validate_look_assignment(
        self,
        data: Dict[str, Any],
        season_index: int,
        designer_index: int,
        look_number: int,
        images: List[Dict[str, str]],
    ) -> bool:
        """Validate look data before assignment."""
        try:
            # Validate season and designer indices
            if not data.get("seasons") or season_index >= len(data["seasons"]):
                self.logger.error(f"Invalid season index: {season_index}")
                return False

            season = data["seasons"][season_index]
            if not season.get("designers") or designer_index >= len(season["designers"]):
                self.logger.error(f"Invalid designer index: {designer_index}")
                return False

            designer = season["designers"][designer_index]

            # Initialize looks array if needed
            if "looks" not in designer:
                designer["looks"] = []

            # Check if look already exists
            existing_look = None
            for look in designer["looks"]:
                if look["look_number"] == look_number:
                    existing_look = look
                    break

            if existing_look and existing_look.get("completed", False):
                self.logger.warning(
                    f"Attempting to modify completed look {look_number} "
                    f"for designer {designer['name']}"
                )
                return False

            self._log_operation(
                "validate_look",
                {
                    "season_index": season_index,
                    "designer_index": designer_index,
                    "look_number": look_number,
                    "image_count": len(images),
                    "timestamp": datetime.now().isoformat(),
                },
            )

            return True

        except Exception as e:
            self.logger.error(f"Look validation error: {str(e)}")
            return False

    def get_designer_by_url(
        self, data: Dict[str, Any], designer_url: str
    ) -> Optional[tuple[int, int]]:
        """Find correct indices for a designer URL."""
        for season_idx, season in enumerate(data["seasons"]):
            for designer_idx, designer in enumerate(season["designers"]):
                if designer["url"] == designer_url:
                    return (season_idx, designer_idx)
        return None

    def _log_operation(self, operation: str, details: Dict[str, Any]) -> None:
        """Log storage operation details."""
        self.operation_log.append({"operation": operation, "details": details})

    def get_operation_log(self) -> List[Dict[str, Any]]:
        """Get log of all storage operations."""
        return self.operation_log

    def analyze_storage_operations(self) -> Dict[str, Any]:
        """Analyze storage operations for patterns and issues."""
        analysis = {
            "total_operations": len(self.operation_log),
            "operations_by_type": {},
            "potential_issues": [],
        }

        last_designer_url = None
        for op in self.operation_log:
            # Track operation types
            op_type = op["operation"]
            analysis["operations_by_type"][op_type] = (
                analysis["operations_by_type"].get(op_type, 0) + 1
            )

            # Check for rapid designer switches
            if op_type == "validate_context":
                current_url = op["details"]["designer_url"]
                if last_designer_url and current_url != last_designer_url:
                    analysis["potential_issues"].append(
                        {
                            "type": "designer_switch",
                            "from_url": last_designer_url,
                            "to_url": current_url,
                            "timestamp": op["details"]["timestamp"],
                        }
                    )
                last_designer_url = current_url

        return analysis

    def validate_season_data(self, season_data: Dict[str, Any]) -> bool:
        """Validate season data structure and content.

        Args:
            season_data: Season data to validate

        Returns:
            bool: True if season data is valid
        """
        try:
            # Check required fields
            required_fields = ["season", "year", "url"]
            if not all(field in season_data for field in required_fields):
                self.logger.error(
                    f"Missing required fields in season data. Required: {required_fields}"
                )
                return False

            # Validate field types
            if not isinstance(season_data["season"], str):
                self.logger.error("Season name must be a string")
                return False

            if not isinstance(season_data["year"], str):
                self.logger.error("Year must be a string")
                return False

            if not isinstance(season_data["url"], str):
                self.logger.error("URL must be a string")
                return False

            # Validate field content
            if not season_data["season"].strip():
                self.logger.error("Season name cannot be empty")
                return False

            if not season_data["year"].strip():
                self.logger.error("Year cannot be empty")
                return False

            if not season_data["url"].startswith("http"):
                self.logger.error("Invalid URL format")
                return False

            self._log_operation(
                "validate_season",
                {
                    "season": season_data["season"],
                    "year": season_data["year"],
                    "timestamp": datetime.now().isoformat(),
                },
            )

            return True

        except Exception as e:
            self.logger.error(f"Season data validation error: {str(e)}")
            return False

    def validate_data_structure(self, data: Dict[str, Any]) -> bool:
        """Validate the overall data structure.

        Args:
            data: Complete data structure to validate

        Returns:
            bool: True if data structure is valid
        """
        try:
            # Check required top-level keys
            required_keys = ["metadata", "seasons"]
            if not all(key in data for key in required_keys):
                self.logger.error(f"Missing required top-level keys: {required_keys}")
                return False

            # Validate metadata structure
            metadata_keys = ["created_at", "last_updated", "overall_progress"]
            if not all(key in data["metadata"] for key in metadata_keys):
                self.logger.error(f"Invalid metadata structure")
                return False

            # Validate overall_progress structure
            progress_keys = [
                "total_seasons",
                "completed_seasons",
                "total_designers",
                "completed_designers",
                "total_looks",
                "extracted_looks",
            ]
            if not all(key in data["metadata"]["overall_progress"] for key in progress_keys):
                self.logger.error(f"Invalid progress tracking structure")
                return False

            # Validate seasons array
            if not isinstance(data["seasons"], list):
                self.logger.error("Seasons must be an array")
                return False

            # Validate individual seasons
            for season in data["seasons"]:
                if not self.validate_season_data(season):
                    return False

            self._log_operation(
                "validate_structure",
                {"timestamp": datetime.now().isoformat(), "season_count": len(data["seasons"])},
            )

            return True

        except Exception as e:
            self.logger.error(f"Data structure validation error: {str(e)}")
            return False
