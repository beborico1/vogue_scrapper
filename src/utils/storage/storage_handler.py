"""Main storage handler that provides a unified interface for storage operations.

This module combines the functionality of data updates and progress tracking
into a single, clean interface for use by other modules.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path

from src.utils.storage.data_updater import DataUpdater
from src.utils.storage.progress_tracker import ProgressTracker
from src.exceptions.errors import StorageError, ValidationError

class DataStorageHandler(DataUpdater):
    """Main storage handler providing a unified interface for all storage operations."""

    def update_data(
        self,
        season_data: Optional[Dict[str, Any]] = None,
        designer_data: Optional[Dict[str, Any]] = None,
        look_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update storage with new data, automatically determining update type.
        
        Args:
            season_data: Optional season data to update
            designer_data: Optional designer data to update
            look_data: Optional look data to update
            
        Returns:
            True if update successful
            
        Raises:
            StorageError: If update fails
            ValidationError: If data validation fails
        """
        try:
            if season_data:
                return self.update_season_data(season_data)
            elif designer_data:
                return self.update_designer_data(
                    designer_data["season_index"],
                    designer_data["data"],
                    designer_data["total_looks"]
                )
            elif look_data:
                return self.update_look_data(
                    look_data["season_index"],
                    look_data["designer_index"],
                    look_data["look_number"],
                    look_data["images"]
                )
            else:
                raise ValidationError("No valid data provided for update")
                
        except Exception as e:
            self.logger.error(f"Error in update_data: {str(e)}")
            return False

    def is_season_completed(self, season: Dict[str, str]) -> bool:
        """Check if a season has been completely processed.
        
        Args:
            season: Season data containing season and year keys
            
        Returns:
            True if season is completed
        """
        try:
            data = self.read_data()
            for stored_season in data["seasons"]:
                if (stored_season["season"] == season["season"] and 
                    stored_season["year"] == season["year"]):
                    return stored_season.get("completed", False)
            return False
        except Exception as e:
            self.logger.error(f"Error checking season completion: {str(e)}")
            return False

    def is_designer_completed(self, designer_url: str) -> bool:
        """Check if a designer's show has been completely processed.
        
        Args:
            designer_url: URL identifier of the designer
            
        Returns:
            True if designer is completed
        """
        try:
            data = self.read_data()
            for season in data["seasons"]:
                for designer in season.get("designers", []):
                    if designer["url"] == designer_url:
                        return designer.get("completed", False)
            return False
        except Exception as e:
            self.logger.error(f"Error checking designer completion: {str(e)}")
            return False

    def get_incomplete_looks(self, designer_url: str) -> List[Dict[str, Any]]:
        """Get information about incomplete looks for a designer.
        
        Args:
            designer_url: URL identifier of the designer
            
        Returns:
            List of incomplete looks with their metadata
        """
        try:
            data = self.read_data()
            for season in data["seasons"]:
                for designer in season.get("designers", []):
                    if designer["url"] == designer_url:
                        incomplete_looks = []
                        
                        for look_num in range(1, designer.get("total_looks", 0) + 1):
                            look_data = None
                            for look in designer.get("looks", []):
                                if look["look_number"] == look_num:
                                    look_data = look
                                    break
                            
                            if not look_data or not look_data.get("completed", False):
                                incomplete_looks.append({
                                    "look_number": look_num,
                                    "existing_images": [
                                        img["type"] 
                                        for img in look_data["images"]
                                    ] if look_data else []
                                })
                        
                        return incomplete_looks
            return []
        except Exception as e:
            self.logger.error(f"Error getting incomplete looks: {str(e)}")
            return []

    def get_progress(self, detailed: bool = False) -> Dict[str, Any]:
        """Get current progress information.
        
        Args:
            detailed: If True, returns detailed progress statistics
            
        Returns:
            Dictionary containing progress information
        """
        try:
            data = self.read_data()
            return (ProgressTracker.get_progress_summary(data) if detailed 
                   else ProgressTracker.get_completion_percentages(data))
        except Exception as e:
            self.logger.error(f"Error getting progress: {str(e)}")
            return {}

    def save_progress(self) -> bool:
        """Update and save current progress information.
        
        Returns:
            True if save successful
        """
        try:
            data = self.read_data()
            updated_data = ProgressTracker.update_overall_progress(data)
            self.write_data(updated_data)
            return True
        except Exception as e:
            self.logger.error(f"Error saving progress: {str(e)}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get current storage status including file info and progress.
        
        Returns:
            Dictionary containing storage status information
        """
        try:
            current_file = self.get_current_file()
            data = self.read_data() if current_file else None
            
            status = {
                "current_file": str(current_file) if current_file else None,
                "initialized": current_file is not None and current_file.exists(),
                "last_updated": None,
                "progress": None
            }
            
            if data:
                status.update({
                    "last_updated": data["metadata"]["last_updated"],
                    "progress": ProgressTracker.get_completion_percentages(data)
                })
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting status: {str(e)}")
            return {
                "current_file": None,
                "initialized": False,
                "error": str(e)
            }

    def validate(self) -> Dict[str, Any]:
        """Validate current storage state and data integrity.
        
        Returns:
            Dictionary containing validation results
        """
        try:
            validation = {
                "valid": False,
                "file_exists": False,
                "data_valid": False,
                "messages": []
            }
            
            # Check file existence
            current_file = self.get_current_file()
            if not current_file:
                validation["messages"].append("No file initialized")
                return validation
            
            validation["file_exists"] = current_file.exists()
            if not validation["file_exists"]:
                validation["messages"].append("File does not exist")
                return validation
            
            # Validate data
            try:
                data = self.read_data()
                validation["data_valid"] = True
                
                # Perform additional data structure checks
                required_fields = ["metadata", "seasons"]
                missing_fields = [field for field in required_fields 
                                if field not in data]
                
                if missing_fields:
                    validation["messages"].append(
                        f"Missing required fields: {', '.join(missing_fields)}"
                    )
                    validation["data_valid"] = False
                
            except Exception as e:
                validation["messages"].append(f"Data validation error: {str(e)}")
                return validation
            
            validation["valid"] = (validation["file_exists"] and 
                                 validation["data_valid"])
            return validation
            
        except Exception as e:
            self.logger.error(f"Error in validation: {str(e)}")
            return {
                "valid": False,
                "error": str(e)
            }