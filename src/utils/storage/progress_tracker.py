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
                "elapsed_time": "0:00:00",
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

            # Calculate current metrics
            total_designers = 0
            completed_designers = 0
            total_looks = 0
            extracted_looks = 0

            # Calculate from actual data
            for season in data.get("seasons", []):
                designers = season.get("designers", [])
                total_designers += len(designers)

                for designer in designers:
                    total_looks += designer.get("total_looks", 0)
                    current_extracted = self._count_designer_looks(designer)
                    extracted_looks += current_extracted
                    if self._is_designer_completed(designer):
                        completed_designers += 1

            # Update metrics
            progress.update(
                {
                    "total_seasons": len(data.get("seasons", [])),
                    "total_designers": total_designers,
                    "completed_designers": completed_designers,
                    "total_looks": total_looks,
                    "extracted_looks": extracted_looks,
                }
            )

            # Calculate time-based metrics
            current_time = datetime.now()
            elapsed = current_time - self.start_time
            progress["elapsed_time"] = str(timedelta(seconds=int(elapsed.total_seconds())))

            # Calculate rate and completion percentage
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

            # Save updates
            data["metadata"]["last_updated"] = current_time.isoformat()
            self.storage.write_data(data)

            # Log progress
            self.logger.info(
                f"Progress: {extracted_looks}/{total_looks} looks "
                f"({progress['completion_percentage']}%) - "
                f"Rate: {progress['extraction_rate']} looks/min"
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
            total_looks = designer.get("total_looks", 0)
            if total_looks == 0:
                return False
            completed_looks = self._count_designer_looks(designer)
            return completed_looks >= total_looks
        except Exception:
            return False

    def update_look_progress(self, season_index: int, designer_index: int) -> None:
        """Update progress after processing a look."""
        try:
            data = self.storage.read_data()
            designer = data["seasons"][season_index]["designers"][designer_index]

            # Count and update completed looks
            completed_looks = self._count_designer_looks(designer)
            designer["extracted_looks"] = completed_looks

            # Update completion status
            total_looks = designer.get("total_looks", 0)
            designer["completed"] = self._is_designer_completed(designer)

            # Save updates and update overall progress
            self.storage.write_data(data)
            self.update_progress()

            # Log designer progress
            self.logger.info(
                f"Designer progress: {completed_looks}/{total_looks} looks "
                f"({'completed' if designer['completed'] else 'in progress'})"
            )

        except Exception as e:
            self.logger.error(f"Error updating look progress: {str(e)}")
