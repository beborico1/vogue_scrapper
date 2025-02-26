"""Designer-related operations for Redis storage.

This module provides designer-related functionality for the Redis storage handler,
including adding, retrieving, and validating designers.
"""

import json
from typing import Dict, Any, Optional

from src.utils.storage.models import Designer, Season
from src.utils.storage.redis.redis_storage_base import RedisStorageBase


class RedisStorageDesignerMixin:
    """Mixin class for designer-related Redis storage operations."""
    
    def add_designer(self, designer_data: Dict[str, Any], season: str, year: str) -> bool:
        """Add or update designer data.
        
        Args:
            designer_data: Designer data dictionary
            season: Season name
            year: Season year
            
        Returns:
            bool: True if successful
        """
        try:
            # Validate required fields
            if not all(key in designer_data for key in ["name", "url"]):
                self.logger.error("Missing required designer fields")
                return False
            
            # Generate keys
            designer_key = self.DESIGNER_KEY_PATTERN.format(url=designer_data["url"])
            season_key = self.SEASON_KEY_PATTERN.format(season=season, year=year)
            
            # Check if designer exists
            designer_exists = self.redis.exists(designer_key)
            
            # Set default total_looks if not provided
            if "total_looks" not in designer_data:
                designer_data["total_looks"] = 0
            
            self.logger.info(f"Adding/updating designer: {designer_data['name']} with total_looks: {designer_data['total_looks']}")
            
            if designer_exists:
                # Load existing designer
                existing_data = json.loads(self.redis.get(designer_key))
                designer = Designer.from_dict(existing_data)
                
                # Update fields while preserving looks
                designer.name = designer_data["name"]
                designer.slideshow_url = designer_data.get("slideshow_url")
                
                # Only update total_looks if the new value is non-zero or greater than existing
                if designer_data.get("total_looks", 0) > 0:
                    designer.total_looks = max(designer_data.get("total_looks", 0), designer.total_looks)
                elif designer.total_looks == 0:
                    designer.total_looks = designer_data.get("total_looks", 0)
            else:
                # Create new designer
                designer = Designer(
                    name=designer_data["name"],
                    url=designer_data["url"],
                    slideshow_url=designer_data.get("slideshow_url"),
                    total_looks=designer_data.get("total_looks", 0)
                )
                
                # Add to designers set
                self.redis.sadd(self.ALL_DESIGNERS_KEY, designer_data["url"])
            
            # Save designer data
            self.redis.set(designer_key, json.dumps(designer.to_dict()))
            
            # Link designer to season
            if self.redis.exists(season_key):
                # Load season
                season_data = json.loads(self.redis.get(season_key))
                season_obj = Season.from_dict(season_data)
                
                # Check if designer already in season
                designer_urls = [d.url for d in season_obj.designers]
                if designer_data["url"] not in designer_urls:
                    # Add designer reference to season with total_looks
                    season_obj.designers.append(Designer(
                        name=designer_data["name"],
                        url=designer_data["url"],
                        total_looks=designer.total_looks  # Use the possibly updated value
                    ))
                    season_obj.total_designers = len(season_obj.designers)
                else:
                    # Update existing designer in season
                    for d in season_obj.designers:
                        if d.url == designer_data["url"]:
                            if designer.total_looks > 0:
                                d.total_looks = designer.total_looks
                            break
                
                # Save updated season
                self.redis.set(season_key, json.dumps(season_obj.to_dict()))
            
            # Update metadata
            self._update_metadata_progress()
            
            self.logger.info(f"Saved designer: {designer_data['name']} with total_looks: {designer.total_looks}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding designer: {str(e)}")
            return False
    
    def get_designer(self, designer_url: str) -> Optional[Dict[str, Any]]:
        """Get designer data by URL.
        
        Args:
            designer_url: Designer URL identifier
            
        Returns:
            Optional[Dict[str, Any]]: Designer data or None if not found
        """
        try:
            designer_key = self.DESIGNER_KEY_PATTERN.format(url=designer_url)
            
            if not self.redis.exists(designer_key):
                return None
            
            designer_data = json.loads(self.redis.get(designer_key))
            return designer_data
            
        except Exception as e:
            self.logger.error(f"Error getting designer: {str(e)}")
            return None
    
    def is_designer_completed(self, designer_url: str) -> bool:
        """Check if a designer's show has been completely processed.
        
        Args:
            designer_url: URL identifier
            
        Returns:
            bool: True if designer completed
        """
        try:
            designer_data = self.get_designer(designer_url)
            if not designer_data:
                return False
            
            return designer_data.get("completed", False)
            
        except Exception as e:
            self.logger.error(f"Error checking designer completion: {str(e)}")
            return False