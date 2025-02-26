"""Progress tracking and metadata handling for Redis storage.

This module provides progress tracking and metadata update functionality
for the Redis storage handler.
"""

import json
from typing import Dict, Any
from datetime import datetime

from src.utils.storage.models import Progress, Metadata


class RedisStorageProgressMixin:
    """Mixin class for Redis storage progress tracking."""
    
    def _update_metadata_progress(self) -> None:
        """Update metadata with current progress statistics."""
        try:
            # Get current metadata
            metadata_str = self.redis.get(self.METADATA_KEY)
            if not metadata_str:
                self._initialize_metadata()
                metadata_str = self.redis.get(self.METADATA_KEY)
            
            metadata = Metadata.from_dict(json.loads(metadata_str))
            
            # Update last_updated
            metadata.last_updated = datetime.now().isoformat()
            
            # Calculate progress statistics
            all_seasons = self.get_all_seasons()
            seasons_count = len(all_seasons)
            completed_seasons = sum(1 for s in all_seasons if s.get("completed", False))
            
            designers_count = self.redis.scard(self.ALL_DESIGNERS_KEY)
            completed_designers = 0
            total_looks = 0
            extracted_looks = 0
            
            # Add detailed logging of season count
            designer_names = []
            self.logger.info(f"Progress update - Found {designers_count} designers in Redis.")
            
            # Count completed designers and looks
            for designer_url in self.redis.smembers(self.ALL_DESIGNERS_KEY):
                designer_key = self.DESIGNER_KEY_PATTERN.format(url=designer_url)
                if self.redis.exists(designer_key):
                    designer_data = json.loads(self.redis.get(designer_key))
                    designer_name = designer_data.get("name", "Unknown")
                    designer_names.append(designer_name)
                    
                    # Count completed designer
                    if designer_data.get("completed", False):
                        completed_designers += 1
                    
                    # Get total looks
                    design_total_looks = designer_data.get("total_looks", 0)
                    total_looks += design_total_looks
                    
                    # Get completed look count from designer data
                    # Make sure to use the stored extracted_looks value
                    completed_look_count = designer_data.get("extracted_looks", 0)
                    
                    # Log for debugging
                    self.logger.info(f"Designer {designer_name}: extracted_looks={completed_look_count}")
                    
                    # Add to overall count
                    extracted_looks += completed_look_count
            
            # Calculate completion percentage
            completion_percentage = 0.0
            if total_looks > 0:
                completion_percentage = round((extracted_looks / total_looks) * 100, 2)
            
            # Log the counts we found and designer names
            self.logger.info(f"Progress update - Total looks: {total_looks}, Extracted looks: {extracted_looks}, Completion: {completion_percentage}%")
            self.logger.info(f"Designers found: {', '.join(designer_names[:5])}{'...' if len(designer_names) > 5 else ''}")
            
            # Get existing progress values to preserve rate and time estimates
            current_progress = metadata.overall_progress
            
            # Update progress with all fields
            metadata.overall_progress = Progress(
                total_seasons=seasons_count,
                completed_seasons=completed_seasons,
                total_designers=designers_count,
                completed_designers=completed_designers,
                total_looks=total_looks,
                extracted_looks=extracted_looks,
                completion_percentage=completion_percentage,
                extraction_rate=current_progress.extraction_rate,
                estimated_completion=current_progress.estimated_completion,
                start_time=current_progress.start_time or datetime.now().isoformat()
            )
            
            # Save updated metadata
            self.redis.set(self.METADATA_KEY, json.dumps(metadata.to_dict()))
            
            # Log the updated metadata for debugging
            self.logger.info(f"Updated metadata progress: {metadata.overall_progress.extracted_looks}/{metadata.overall_progress.total_looks} looks")
            
        except Exception as e:
            self.logger.error(f"Error updating metadata progress: {str(e)}")