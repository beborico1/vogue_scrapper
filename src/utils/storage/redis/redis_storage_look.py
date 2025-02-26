"""Look-related operations for Redis storage.

This module provides look and image-related functionality for the Redis storage handler,
including adding, retrieving, and validating looks and images.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.utils.storage.models import Look, Image, Designer, Season
from src.utils.storage.redis.redis_storage_base import RedisStorageBase


class RedisStorageLookMixin:
    """Mixin class for look-related Redis storage operations."""
    
    def add_look(self, designer_url: str, look_number: int, images: List[Dict[str, Any]]) -> bool:
        """Add or update look data.
        
        Args:
            designer_url: Designer URL identifier
            look_number: Look number
            images: List of image data
            
        Returns:
            bool: True if successful
        """
        try:
            # Generate keys
            designer_key = self.DESIGNER_KEY_PATTERN.format(url=designer_url)
            look_key = self.LOOK_KEY_PATTERN.format(
                designer_url=designer_url,
                look_number=look_number
            )
            
            # Validate designer exists
            if not self.redis.exists(designer_key):
                self.logger.error(f"Designer not found: {designer_url}")
                return False
            
            # Load designer data first
            designer_data = json.loads(self.redis.get(designer_key))
            designer = Designer.from_dict(designer_data)
            
            # Update total_looks if needed based on the look number
            if look_number > designer.total_looks:
                self.logger.info(f"Updating total_looks based on look number: {designer.total_looks} -> {look_number}")
                designer.total_looks = look_number
            
            # Check if look exists
            look_exists = self.redis.exists(look_key)
            
            if look_exists:
                # Load existing look
                existing_data = json.loads(self.redis.get(look_key))
                look = Look.from_dict(existing_data)
            else:
                # Create new look
                look = Look(look_number=look_number)
            
            # Process images
            timestamp = datetime.now().isoformat()
            processed_images = []
            
            for img_data in images:
                # Validate image data
                if not all(key in img_data for key in ["url"]):
                    continue
                
                # Create image object
                image = Image(
                    url=img_data["url"],
                    look_number=look_number,
                    alt_text=img_data.get("alt_text", f"Look {look_number}"),
                    type=img_data.get("type", "default"),
                    timestamp=timestamp
                )
                processed_images.append(image)
            
            if not processed_images:
                self.logger.warning(f"No valid images found for look {look_number}")
                return False
            
            # Replace images to avoid duplicates
            if look_exists:
                look.images = processed_images
            else:
                look.images = processed_images
                
            look.completed = True
            
            # Save look data
            self.redis.set(look_key, json.dumps(look.to_dict()))
            
            # Find or create look in designer
            look_exists_in_designer = False
            for i, l in enumerate(designer.looks):
                if l.look_number == look_number:
                    designer.looks[i].completed = True
                    designer.looks[i].images = processed_images  # Update with the latest images
                    look_exists_in_designer = True
                    break
            
            if not look_exists_in_designer:
                # Create a look with images
                new_look = Look(look_number=look_number, completed=True)
                new_look.images = processed_images
                designer.looks.append(new_look)
            
            # Sort looks in designer
            designer.looks.sort(key=lambda x: x.look_number)
            
            # Count extracted_looks directly based on the look data
            designer.extracted_looks = sum(1 for l in designer.looks if l.completed and l.images)
            
            # Update completion status
            designer.completed = designer.extracted_looks >= designer.total_looks
            
            # Save updated designer
            self.redis.set(designer_key, json.dumps(designer.to_dict()))
            
            # Update all season references to this designer
            self._update_seasons_with_designer(designer_url, designer)
            
            # Update metadata
            self._update_metadata_progress()
            
            self.logger.info(f"Saved look {look_number} with {len(processed_images)} images. Designer has {designer.extracted_looks}/{designer.total_looks} looks completed.")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding look: {str(e)}")
            return False
    
    def get_look(self, designer_url: str, look_number: int) -> Optional[Dict[str, Any]]:
        """Get look data by designer URL and look number.
        
        Args:
            designer_url: Designer URL identifier
            look_number: Look number
            
        Returns:
            Optional[Dict[str, Any]]: Look data or None if not found
        """
        try:
            look_key = self.LOOK_KEY_PATTERN.format(
                designer_url=designer_url,
                look_number=look_number
            )
            
            if not self.redis.exists(look_key):
                return None
            
            look_data = json.loads(self.redis.get(look_key))
            return look_data
            
        except Exception as e:
            self.logger.error(f"Error getting look: {str(e)}")
            return None
    
    def _update_seasons_with_designer(self, designer_url: str, designer: Designer) -> None:
        """Update all season references to a designer.
        
        Args:
            designer_url: Designer URL
            designer: Updated Designer object
        """
        for season_id in self.redis.smembers(self.ALL_SEASONS_KEY):
            season_name, year = season_id.split(":")
            season_key = self.SEASON_KEY_PATTERN.format(season=season_name, year=year)
            
            if self.redis.exists(season_key):
                season_data = json.loads(self.redis.get(season_key))
                season_obj = Season.from_dict(season_data)
                
                # Find this designer in the season
                for i, d in enumerate(season_obj.designers):
                    if d.url == designer_url:
                        # Update the designer reference
                        season_obj.designers[i].total_looks = designer.total_looks
                        season_obj.designers[i].extracted_looks = designer.extracted_looks
                        season_obj.designers[i].completed = designer.completed
                        
                        # Update completed_designers count
                        season_obj.completed_designers = sum(1 for d in season_obj.designers if d.completed)
                        season_obj.completed = season_obj.completed_designers >= season_obj.total_designers
                        
                        # Save the updated season
                        self.redis.set(season_key, json.dumps(season_obj.to_dict()))
                        break
    
    def update_look_data(self, season_index: int, designer_index: int, look_number: int, images: List[Dict[str, Any]]) -> bool:
        """Update look data (compatibility method).
        
        Args:
            season_index: Index of the season
            designer_index: Index of the designer
            look_number: Look number
            images: List of image data
            
        Returns:
            bool: True if successful
        """
        try:
            # Read data to find designer URL
            data = self.read_data()
            
            if season_index >= len(data["seasons"]):
                self.logger.error(f"Invalid season index: {season_index}")
                return False
                
            season = data["seasons"][season_index]
            
            if designer_index >= len(season.get("designers", [])):
                self.logger.error(f"Invalid designer index: {designer_index}")
                return False
                
            designer = season["designers"][designer_index]
            designer_url = designer.get("url")
            
            if not designer_url:
                self.logger.error("Missing designer URL")
                return False
            
            # Add look directly to Redis
            result = self.add_look(designer_url, look_number, images)
            
            # Force a metadata refresh to ensure counts are up to date
            self._update_metadata_progress()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error updating look data: {str(e)}")
            return False