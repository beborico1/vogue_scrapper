# src/utils/storage/completion_storage_handler.py
"""Completion status management for storage operations."""

from typing import Dict, Any

from .session_storage_handler import SessionStorageHandler


class CompletionStorageHandler(SessionStorageHandler):
    """Handles completion status checks and updates for seasons, designers, and looks."""

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