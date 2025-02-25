"""Progress tracker for monitoring data collection progress."""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import time
import json


class ProgressTracker:
    """Handles progress tracking, statistics calculations, and data processing."""

    def __init__(self, storage: Any, logger: Any):
        """Initialize the ProgressTracker.

        Args:
            storage: Storage interface for data persistence
            logger: Logger instance for tracking operations
        """
        self.storage = storage
        self.logger = logger
        self.start_time = datetime.now()
        self.last_extraction_time = self.start_time
        self.previous_extracted_count = 0

        # Initialize base metrics
        self.initialize_metrics()

    def initialize_metrics(self) -> None:
        """Initialize or update progress metrics in storage."""
        try:
            data = self.storage.read_data()

            # Ensure metadata structure exists
            if "metadata" not in data:
                data["metadata"] = {}

            if "overall_progress" not in data["metadata"]:
                data["metadata"]["overall_progress"] = {}

            progress = data["metadata"]["overall_progress"]

            # Define default metrics if not present
            default_metrics = {
                "total_seasons": len(data.get("seasons", [])),
                "completed_seasons": 0,
                "total_designers": 0,
                "completed_designers": 0,
                "total_looks": 0,
                "extracted_looks": 0,
                "start_time": self.start_time.isoformat(),
                "estimated_completion": "Unknown",
                "completion_percentage": 0.0,
                "extraction_rate": 0.0,
            }

            # Update missing metrics
            for key, default_value in default_metrics.items():
                if key not in progress:
                    progress[key] = default_value

            # Update timestamp
            data["metadata"]["last_updated"] = datetime.now().isoformat()

            # Save initialized data
            self.storage.write_data(data)

        except Exception as e:
            self.logger.error(f"Error initializing metrics: {str(e)}")

    def update_progress(self, force_save: bool = True) -> None:
        """Update overall progress metrics."""
        try:
            data = self.storage.read_data()
            progress = data["metadata"]["overall_progress"]

            # Add debug logging
            self.logger.info(f"DEBUG: Starting progress update. Current data: {json.dumps(progress)}")

            # Calculate current metrics with care for each counter
            total_designers = 0
            completed_designers = 0
            total_looks = 0
            extracted_looks = 0
            completed_seasons = 0

            # Calculate from actual data with precise counting
            for season in data.get("seasons", []):
                designers = season.get("designers", [])
                season_designers = len(designers)
                total_designers += season_designers
                
                # Count designers with completed flag explicitly true
                season_completed_designers = sum(1 for d in designers if d.get("completed") is True)
                completed_designers += season_completed_designers
                
                # Update season completion count
                season["completed_designers"] = season_completed_designers
                
                # Mark season as completed if all designers are completed
                season["completed"] = (season_completed_designers >= season_designers) if season_designers > 0 else False
                if season["completed"]:
                    completed_seasons += 1

                # Count looks with detailed logging
                for designer in designers:
                    designer_total_looks = designer.get("total_looks", 0)
                    total_looks += designer_total_looks
                    
                    # Count completed looks and log details
                    designer_looks = designer.get("looks", [])
                    designer_completed_looks = 0
                    
                    # Add debug for each designer's looks
                    self.logger.info(f"DEBUG: Designer {designer.get('name')} has {len(designer_looks)} looks in data")
                    
                    for look in designer_looks:
                        # Log each look's completion status and image count for debugging
                        look_completed = look.get("completed", False)
                        look_has_images = "images" in look and look["images"]
                        look_num = look.get("look_number", "unknown")
                        
                        self.logger.info(f"DEBUG: Look {look_num} - completed: {look_completed}, has_images: {look_has_images}, image count: {len(look.get('images', []))}")
                        
                        if look_completed and look_has_images:
                            designer_completed_looks += 1
                    
                    self.logger.info(f"DEBUG: Designer {designer.get('name')} has {designer_completed_looks} completed looks out of {designer_total_looks} total")
                    
                    extracted_looks += designer_completed_looks
                    
                    # Update designer extracted_looks count
                    designer["extracted_looks"] = designer_completed_looks
                    
                    # Update designer completion status
                    designer["completed"] = (designer_completed_looks >= designer_total_looks) if designer_total_looks > 0 else False

            # Update metrics with accurate counts
            progress.update({
                "total_seasons": len(data.get("seasons", [])),
                "completed_seasons": completed_seasons,
                "total_designers": total_designers,
                "completed_designers": completed_designers,
                "total_looks": total_looks,
                "extracted_looks": extracted_looks,
            })
            
            self.logger.info(f"DEBUG: Updated progress counts - extracted_looks: {extracted_looks}, total_looks: {total_looks}")

            # Update timestamp
            current_time = datetime.now()

            # Calculate completion percentage
            if total_looks > 0:
                progress["completion_percentage"] = round((extracted_looks / total_looks) * 100, 2)

                # Calculate extraction rate
                time_diff = (current_time - self.last_extraction_time).total_seconds() / 60
                if time_diff > 0 and extracted_looks > self.previous_extracted_count:
                    rate = (extracted_looks - self.previous_extracted_count) / time_diff
                    progress["extraction_rate"] = round(rate, 2)

                    # Update estimated completion
                    if rate > 0:
                        remaining_looks = total_looks - extracted_looks
                        remaining_minutes = remaining_looks / rate
                        estimated_completion = current_time + timedelta(minutes=remaining_minutes)
                        progress["estimated_completion"] = estimated_completion.isoformat()

                    # Update tracking variables
                    self.last_extraction_time = current_time
                    self.previous_extracted_count = extracted_looks

            # Save updates if requested
            data["metadata"]["last_updated"] = current_time.isoformat()
            if force_save:
                self.storage.write_data(data)
                self.logger.info(f"DEBUG: Saved updated progress to storage")

            # Log progress with detailed counts
            self.logger.info(
                f"Overall Progress: {extracted_looks}/{total_looks} looks "
                f"({progress['completion_percentage']}%) - "
                f"Designers: {completed_designers}/{total_designers} completed - "
                f"Seasons: {completed_seasons}/{len(data.get('seasons', []))} completed"
            )

        except Exception as e:
            self.logger.error(f"Error updating progress: {str(e)}")

    def _count_designer_looks(self, designer: Dict[str, Any]) -> int:
        """Count completed looks for a designer."""
        try:
            return sum(1 for look in designer.get("looks", []) if self._is_look_completed(look))
        except Exception:
            return 0

    def _is_look_completed(self, look: Dict[str, Any]) -> bool:
        """Check if a look is completed."""
        try:
            if not look.get("images"):
                return False
            return any(all(key in img for key in ["url", "look_number"]) for img in look["images"])
        except Exception:
            return False

    def _is_designer_completed(self, designer: Dict[str, Any]) -> bool:
        """Check if a designer is completed."""
        try:
            # First check if designer has an explicit completed flag set
            if designer.get("completed") is True:
                return True
                
            total_looks = designer.get("total_looks", 0)
            if total_looks == 0:
                return False
                
            # Count completed looks
            completed_looks = self._count_designer_looks(designer)
            
            # Strict equality check
            return completed_looks >= total_looks
        except Exception as e:
            self.logger.error(f"Error checking designer completion: {str(e)}")
            return False

    def update_look_progress(self, season_index: int, designer_index: int) -> None:
        """Update progress after processing a look."""
        try:
            data = self.storage.read_data()
            
            # Make sure indexes are valid
            if (season_index >= len(data["seasons"]) or
                designer_index >= len(data["seasons"][season_index]["designers"])):
                self.logger.error(f"Invalid indices: season_index={season_index}, designer_index={designer_index}")
                return
                
            designer = data["seasons"][season_index]["designers"][designer_index]
            season = data["seasons"][season_index]

            # Count and update completed looks
            completed_looks = self._count_designer_looks(designer)
            designer["extracted_looks"] = completed_looks

            # Update completion status
            total_looks = designer.get("total_looks", 0)
            
            # Strict completion check
            designer["completed"] = (completed_looks >= total_looks) if total_looks > 0 else False
            
            # Update season completion counts
            season["completed_designers"] = sum(1 for d in season["designers"] if d.get("completed", False))
            
            # Save updates and update overall progress
            self.storage.write_data(data)
            self.update_progress(force_save=False)  # Already saved above

            # Log designer progress
            self.logger.info(
                f"Designer: {designer.get('name', 'Unknown')} - "
                f"Progress: {completed_looks}/{total_looks} looks "
                f"({'completed' if designer['completed'] else 'in progress'}) - "
                f"Season {season['season']} {season['year']}: "
                f"{season['completed_designers']}/{len(season['designers'])} designers completed"
            )

        except Exception as e:
            self.logger.error(f"Error updating look progress: {str(e)}")
