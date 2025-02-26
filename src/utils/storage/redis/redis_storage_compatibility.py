"""Compatibility layer for Redis storage.

This module provides compatibility methods to make the Redis storage handler
work with the same interface as the JSON storage handler.
"""

import json
import tempfile
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from src.utils.storage.models import Progress, Metadata


class RedisStorageCompatibilityMixin:
    """Mixin class for Redis storage compatibility methods."""
    
    def read_data(self) -> Dict[str, Any]:
        """Read current data (compatibility method).
        
        Returns:
            Dict containing metadata and seasons
        """
        try:
            return {
                "metadata": self.get_metadata(),
                "seasons": self.get_all_seasons()
            }
        except Exception as e:
            self.logger.error(f"Error reading data: {str(e)}")
            return {"metadata": {}, "seasons": []}
        
    def write_data(self, data: Dict[str, Any]) -> None:
        """Write data (compatibility method).
        
        Args:
            data: Dict containing metadata and seasons
        """
        try:
            # Extract metadata and write it
            metadata = data.get("metadata", {})
            if metadata:
                self.redis.set(self.METADATA_KEY, json.dumps(metadata))
                
            # Process seasons
            seasons = data.get("seasons", [])
            for season_data in seasons:
                if not all(key in season_data for key in ["season", "year"]):
                    continue
                    
                # Add season
                self.add_season(season_data)
                
                # Process designers
                for designer_data in season_data.get("designers", []):
                    if not all(key in designer_data for key in ["name", "url"]):
                        continue
                        
                    # Add designer
                    self.add_designer(
                        designer_data,
                        season_data["season"],
                        season_data["year"]
                    )
                    
                    # Process looks
                    for look_data in designer_data.get("looks", []):
                        if not all(key in look_data for key in ["look_number"]) or "images" not in look_data:
                            continue
                            
                        # Add look
                        self.add_look(
                            designer_data["url"],
                            look_data["look_number"],
                            look_data.get("images", [])
                        )
            
            self.logger.info("Data written to Redis")
            
        except Exception as e:
            self.logger.error(f"Error writing data: {str(e)}")
            
    def get_current_file(self) -> Optional[Path]:
        """Get current file path (compatibility method).
        
        For Redis, we don't have a file, so we create a temporary one with
        current data for compatibility with scripts that expect files.
        
        Returns:
            Path to temporary file or None if creation failed
        """
        try:
            import tempfile
            from pathlib import Path
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                prefix="vogue_redis_", 
                suffix=".json",
                delete=False,
                mode='w'
            )
            
            # Get all data
            data = self.read_data()
            
            # Write data to temporary file
            json.dump(data, temp_file, indent=2)
            temp_file.close()
            
            self.logger.info(f"Created temporary file at {temp_file.name} for compatibility")
            
            # Store the temp file path
            self._current_temp_file = Path(temp_file.name)
            return self._current_temp_file
            
        except Exception as e:
            self.logger.error(f"Error creating temporary file: {str(e)}")
            return None
    
    def update_data(self, season_data: Optional[Dict[str, Any]] = None,
                    designer_data: Optional[Dict[str, Any]] = None,
                    look_data: Optional[Dict[str, Any]] = None) -> bool:
        """Update data (compatibility method).
        
        Args:
            season_data: Optional season data
            designer_data: Optional designer data
            look_data: Optional look data
            
        Returns:
            bool: True if successful
        """
        try:
            if season_data:
                return self.add_season(season_data)
            
            if designer_data:
                season_index = designer_data.get("season_index", 0)
                # Find season for this index
                seasons = self.get_all_seasons()
                if season_index >= len(seasons):
                    self.logger.error(f"Season index out of range: {season_index}")
                    return False
                
                season = seasons[season_index]
                return self.add_designer(
                    designer_data["data"], 
                    season["season"], 
                    season["year"]
                )
            
            if look_data:
                return self.update_look_data(
                    look_data.get("season_index", 0),
                    look_data.get("designer_index", 0),
                    look_data.get("look_number", 0),
                    look_data.get("images", [])
                )
            
            self.logger.error("No valid data provided")
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating data: {str(e)}")
            return False
    
    def save_progress(self) -> None:
        """Save current progress (compatibility method)."""
        # In Redis, progress is saved in real-time, so we just update metadata
        try:
            self._update_metadata_progress()
            self.logger.info("Progress saved")
        except Exception as e:
            self.logger.error(f"Error saving progress: {str(e)}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scraping status and progress.
        
        Returns:
            Dict with status information
        """
        try:
            # Force an update of progress metrics to ensure data is current
            self._update_metadata_progress()
            
            # Get the updated metadata
            metadata = self.get_metadata()
            progress = metadata.get("overall_progress", {})
            
            # Ensure all required fields are present in the progress data
            if "completion_percentage" not in progress:
                progress["completion_percentage"] = 0.0
            if "extraction_rate" not in progress:
                progress["extraction_rate"] = 0.0
            if "estimated_completion" not in progress:
                progress["estimated_completion"] = None
            if "start_time" not in progress:
                progress["start_time"] = datetime.now().isoformat()
            
            # Create complete status object with all progress fields
            status = {
                "total_seasons": progress.get("total_seasons", 0),
                "completed_seasons": progress.get("completed_seasons", 0),
                "total_designers": progress.get("total_designers", 0),
                "completed_designers": progress.get("completed_designers", 0),
                "total_looks": progress.get("total_looks", 0),
                "extracted_looks": progress.get("extracted_looks", 0),
                "completion_percentage": progress.get("completion_percentage", 0.0),
                "extraction_rate": progress.get("extraction_rate", 0.0),
                "instance_id": self.instance_id,
                "progress": progress,  # For VogueRunwayScraper compatibility
            }
            
            # Log status for debugging
            self.logger.info(f"Status requested - Progress: {status['extracted_looks']}/{status['total_looks']} looks ({status['completion_percentage']}%)")
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting status: {str(e)}")
            return {}