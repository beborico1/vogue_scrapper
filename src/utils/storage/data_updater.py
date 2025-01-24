"""Data updater for handling all storage update operations.

This module extends the base storage handler to provide functionality for
updating season data, designer data, and look data in real-time.
"""

from datetime import datetime
from typing import Dict, Any, List

from src.utils.storage.base_handler import BaseStorageHandler
from src.utils.storage.utils import determine_image_type
from src.exceptions.errors import StorageError, ValidationError


class DataUpdater(BaseStorageHandler):
    """Handles data updates for seasons, designers, and looks."""

    def update_season_data(self, season_data: Dict[str, Any]) -> bool:
        """Update file with new season data in real-time.

        Args:
            season_data: Season data to update including season and year

        Returns:
            True if update successful

        Raises:
            StorageError: If update fails
        """
        try:
            if not self.current_file:
                self.initialize_file()

            current_data = self.read_data()

            # Check if season already exists
            season_exists = False
            for i, existing_season in enumerate(current_data["seasons"]):
                if (
                    existing_season["season"] == season_data["season"]
                    and existing_season["year"] == season_data["year"]
                ):
                    # Preserve existing fields
                    preserved_fields = {
                        "designers": existing_season.get("designers", []),
                        "completed": existing_season.get("completed", False),
                        "total_designers": existing_season.get("total_designers", 0),
                        "completed_designers": existing_season.get("completed_designers", 0),
                    }

                    # Update with new data while preserving fields
                    current_data["seasons"][i].update(season_data)
                    current_data["seasons"][i].update(preserved_fields)

                    season_exists = True
                    break

            if not season_exists:
                # Add new season with required fields
                season_data.update(
                    {
                        "completed": False,
                        "total_designers": 0,
                        "completed_designers": 0,
                        "designers": [],
                    }
                )
                current_data["seasons"].append(season_data)

            current_data["metadata"]["last_updated"] = datetime.now().isoformat()

            self.write_data(current_data)
            self.logger.info(
                f"Updated season: {season_data.get('season')} {season_data.get('year')}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error updating season data: {str(e)}")
            return False

    def update_designer_data(
        self, season_index: int, designer_data: Dict[str, Any], total_looks: int
    ) -> bool:
        """Update file with new designer data in real-time.

        Args:
            season_index: Index of the season in the data structure
            designer_data: Designer data to update
            total_looks: Total number of looks in the collection

        Returns:
            True if update successful

        Raises:
            StorageError: If update fails
            ValidationError: If indices are invalid
        """
        try:
            if not self.current_file:
                self.initialize_file()

            current_data = self.read_data()

            if season_index >= len(current_data["seasons"]):
                raise ValidationError(f"Season index {season_index} out of range")

            season = current_data["seasons"][season_index]

            # Check if designer already exists
            designer_exists = False
            for i, existing_designer in enumerate(season["designers"]):
                if existing_designer["url"] == designer_data["url"]:
                    # Preserve existing fields
                    preserved_fields = {
                        "looks": existing_designer.get("looks", []),
                        "completed": existing_designer.get("completed", False),
                        "extracted_looks": existing_designer.get("extracted_looks", 0),
                    }

                    # Update with new data and totals
                    designer_data.update({"total_looks": total_looks, **preserved_fields})

                    season["designers"][i] = designer_data
                    designer_exists = True
                    break

            if not designer_exists:
                # Add new designer with required fields
                designer_data.update(
                    {
                        "total_looks": total_looks,
                        "extracted_looks": 0,
                        "completed": False,
                        "looks": [],
                    }
                )
                season["designers"].append(designer_data)

            # Update progress counters
            season["total_designers"] = len(season["designers"])
            season["completed_designers"] = sum(1 for d in season["designers"] if d["completed"])
            season["completed"] = season["completed_designers"] >= season["total_designers"]

            current_data["metadata"]["last_updated"] = datetime.now().isoformat()

            self.write_data(current_data)
            self.logger.info(f"Updated designer: {designer_data.get('name')}")
            return True

        except Exception as e:
            self.logger.error(f"Error updating designer data: {str(e)}")
            return False

    def update_look_data(
        self, season_index: int, designer_index: int, look_number: int, images: List[Dict[str, str]]
    ) -> bool:
        """Update file with new look data in real-time.

        Args:
            season_index: Index of the season in the data structure
            designer_index: Index of the designer in the season
            look_number: Number of the look being updated
            images: List of image data for the look

        Returns:
            True if update successful

        Raises:
            StorageError: If update fails
            ValidationError: If indices are invalid
        """
        try:
            if not self.current_file:
                self.initialize_file()

            current_data = self.read_data()

            if season_index >= len(current_data["seasons"]):
                raise ValidationError(f"Season index {season_index} out of range")

            season = current_data["seasons"][season_index]
            if designer_index >= len(season["designers"]):
                raise ValidationError(f"Designer index {designer_index} out of range")

            designer = season["designers"][designer_index]

            if "looks" not in designer:
                designer["looks"] = []

            # Find or create look entry
            look_entry = self._get_or_create_look(designer, look_number)

            # Update images with timestamps and types, preventing duplicates
            timestamp = datetime.now().isoformat()
            processed_images = self._process_images(images, timestamp)

            # Only add non-duplicate images
            new_images = []
            for new_image in processed_images:
                if not self._is_duplicate_image(look_entry["images"], new_image):
                    new_images.append(new_image)

            if new_images:  # Only update if there are new images
                look_entry["images"].extend(new_images)
                look_entry["completed"] = True

                # Sort and update progress
                self._sort_looks(designer)
                self._update_completion_status(designer, season)

                current_data["metadata"]["last_updated"] = timestamp

                self.write_data(current_data)
                self.logger.info(f"Updated look {look_number} with {len(new_images)} new images")

            return True

        except Exception as e:
            self.logger.error(f"Error updating look data: {str(e)}")
            return False

    def _is_duplicate_image(
        self, existing_images: List[Dict[str, str]], new_image: Dict[str, str]
    ) -> bool:
        """Check if an image already exists in the look's images.

        Args:
            existing_images: List of existing images
            new_image: New image to check

        Returns:
            bool: True if image is a duplicate
        """
        for existing in existing_images:
            if existing["url"] == new_image["url"]:
                return True
        return False

    def _get_or_create_look(self, designer: Dict[str, Any], look_number: int) -> Dict[str, Any]:
        """Get existing look entry or create new one.

        Args:
            designer: Designer data dictionary
            look_number: Number of the look

        Returns:
            Look entry dictionary
        """
        for look in designer["looks"]:
            if look["look_number"] == look_number:
                return look

        look_entry = {"look_number": look_number, "completed": False, "images": []}
        designer["looks"].append(look_entry)
        return look_entry

    def _process_images(self, images: List[Dict[str, str]], timestamp: str) -> List[Dict[str, str]]:
        """Process images adding timestamps and determining types.

        Args:
            images: List of image dictionaries
            timestamp: Timestamp to add to images

        Returns:
            List[Dict[str, str]]: Processed images
        """
        processed_images = []
        for image in images:
            processed_image = image.copy()
            if "type" not in processed_image:
                processed_image["type"] = determine_image_type(processed_image.get("alt_text", ""))
            processed_image["timestamp"] = timestamp
            processed_images.append(processed_image)
        return processed_images

    def _sort_looks(self, designer: Dict[str, Any]) -> None:
        """Sort looks by look number.

        Args:
            designer: Designer data dictionary
        """
        designer["looks"].sort(key=lambda x: x["look_number"])

    def _update_completion_status(self, designer: Dict[str, Any], season: Dict[str, Any]) -> None:
        """Update completion status for designer and season.

        Args:
            designer: Designer data dictionary
            season: Season data dictionary
        """
        # Count looks that have valid images and are marked complete
        completed_looks = sum(
            1 for look in designer["looks"] if look["completed"] and look["images"]
        )

        designer["extracted_looks"] = completed_looks
        designer["completed"] = (
            completed_looks >= designer["total_looks"]
            if designer.get("total_looks", 0) > 0
            else False
        )

        # Update season completion based on all designers
        completed_designers = sum(
            1 for d in season["designers"] if d["completed"] and d.get("total_looks", 0) > 0
        )

        season["completed_designers"] = completed_designers
        season["completed"] = (
            completed_designers >= season["total_designers"]
            if season.get("total_designers", 0) > 0
            else False
        )
