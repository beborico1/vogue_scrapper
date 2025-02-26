# src/utils/storage/data_storage_handler.py
"""Enhanced storage handler with validation, session management, and safety checks.

This module provides a robust implementation of the storage handler with:
- Strong data validation
- Session-based processing
- Atomic updates
- Error recovery
- Comprehensive logging
"""

from typing import Dict, Any, Optional
from datetime import datetime

from .validation_storage_handler import ValidationStorageHandler
from ...exceptions.errors import StorageError, ValidationError


class DataStorageHandler(ValidationStorageHandler):
    """Enhanced storage handler with validation and safety checks."""

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

    def update_look_data(
        self, season_index: int, designer_index: int, look_number: int, images
    ) -> bool:
        """Update look data safely.

        This method adds an extra validation layer before passing to the parent implementation.

        Args:
            season_index: Index of the season
            designer_index: Index of the designer
            look_number: Look number to update
            images: List of image data

        Returns:
            bool: True if update successful
        """
        try:
            if not self._active_session:
                self.logger.warning("Updating look data outside of an active session")

            # Validate look data format
            for image in images:
                if not all(key in image for key in ["url", "look_number"]):
                    self.logger.error("Invalid image data format")
                    return False

            return super().update_look_data(season_index, designer_index, look_number, images)
        except Exception as e:
            self.logger.error(f"Error updating look data: {str(e)}")
            return False

    def validate_designer_context(
        self, season_index: int, designer_index: int, designer_url: str
    ) -> bool:
        """Validate that the provided context references the correct designer.

        Args:
            season_index: Index of the season
            designer_index: Index of the designer
            designer_url: URL of the designer for validation

        Returns:
            bool: True if context is valid
        """
        try:
            current_data = self.read_data()
            
            # Check if season index is valid
            if season_index >= len(current_data["seasons"]):
                self.logger.error(f"Invalid season index: {season_index}")
                return False
                
            season = current_data["seasons"][season_index]
            
            # Check if designer index is valid
            if designer_index >= len(season.get("designers", [])):
                self.logger.error(f"Invalid designer index: {designer_index}")
                return False
                
            # Check if designer URL matches
            designer = season["designers"][designer_index]
            if designer["url"] != designer_url:
                self.logger.error(f"Designer URL mismatch: expected {designer_url}, found {designer['url']}")
                return False
                
            return True
                
        except Exception as e:
            self.logger.error(f"Error validating designer context: {str(e)}")
            return False
            
    def safe_operation(self, operation_func, *args, **kwargs):
        """Execute a storage operation with automatic restore point creation.
        
        Args:
            operation_func: Function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            
        Returns:
            Any: Result of the operation
        """
        try:
            # Create restore point
            self._create_restore_point()
            
            # Execute operation
            result = operation_func(*args, **kwargs)
            
            if result:
                self._log_successful_update()
            else:
                self._restore_from_last_point()
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error in safe operation: {str(e)}")
            self._restore_from_last_point()
            return False