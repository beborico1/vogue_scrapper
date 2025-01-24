from typing import Dict, Any, List
from ...exceptions.errors import ValidationError


class DataValidator:
    """Handles data validation and integrity checks."""

    def __init__(self, logger):
        self.logger = logger
        self._operation_log = []

    def validate_data_structure(self, data: Dict[str, Any]) -> bool:
        """Validate the overall data structure."""
        try:
            required_keys = ["metadata", "seasons"]
            metadata_keys = ["created_at", "last_updated", "overall_progress"]

            if not all(key in data for key in required_keys):
                return False

            if not all(key in data["metadata"] for key in metadata_keys):
                return False

            for season in data["seasons"]:
                if not all(key in season for key in ["season", "year", "url", "designers"]):
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Data structure validation error: {str(e)}")
            return False

    def validate_look_data(self, look_data: Dict[str, Any]) -> bool:
        """Validate look data structure and content."""
        try:
            required_fields = ["season_index", "designer_index", "look_number", "images"]
            if not all(field in look_data for field in required_fields):
                return False

            for image in look_data["images"]:
                if not all(key in image for key in ["url", "look_number", "alt_text"]):
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Look data validation error: {str(e)}")
            return False

    def get_operation_log(self) -> List[Dict[str, Any]]:
        """Get log of all storage operations."""
        return self._operation_log
