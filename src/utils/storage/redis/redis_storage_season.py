"""Season-related operations for Redis storage.

This module provides season-related functionality for the Redis storage handler,
including adding, retrieving, and validating seasons.
"""

import json
from typing import Dict, Any, List, Optional

from src.utils.storage.models import Season
from src.utils.storage.redis.redis_storage_base import RedisStorageBase


class RedisStorageSeasonMixin:
    """Mixin class for season-related Redis storage operations."""
    
    def add_season(self, season_data: Dict[str, Any]) -> bool:
        """Add or update season data.
        
        Args:
            season_data: Season data dictionary
            
        Returns:
            bool: True if successful
        """
        try:
            # Validate required fields
            if not all(key in season_data for key in ["season", "year", "url"]):
                self.logger.error("Missing required season fields")
                return False
            
            # Generate season key
            season_key = self.SEASON_KEY_PATTERN.format(
                season=season_data["season"], 
                year=season_data["year"]
            )
            
            # Check if season exists
            season_exists = self.redis.exists(season_key)
            
            if season_exists:
                # Load existing season
                existing_data = json.loads(self.redis.get(season_key))
                season = Season.from_dict(existing_data)
                
                # Update fields while preserving designers
                season.url = season_data["url"]
            else:
                # Create new season
                season = Season(
                    season=season_data["season"],
                    year=season_data["year"],
                    url=season_data["url"]
                )
                
                # Add to seasons set
                self.redis.sadd(self.ALL_SEASONS_KEY, f"{season_data['season']}:{season_data['year']}")
            
            # Save season data
            self.redis.set(season_key, json.dumps(season.to_dict()))
            
            # Update metadata
            self._update_metadata_progress()
            
            self.logger.info(f"Saved season: {season_data['season']} {season_data['year']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding season: {str(e)}")
            return False
    
    def get_season(self, season: str, year: str) -> Optional[Dict[str, Any]]:
        """Get season data by season name and year.
        
        Args:
            season: Season name
            year: Season year
            
        Returns:
            Optional[Dict[str, Any]]: Season data or None if not found
        """
        try:
            season_key = self.SEASON_KEY_PATTERN.format(season=season, year=year)
            
            if not self.redis.exists(season_key):
                return None
            
            season_data = json.loads(self.redis.get(season_key))
            return season_data
            
        except Exception as e:
            self.logger.error(f"Error getting season: {str(e)}")
            return None
    
    def get_all_seasons(self) -> List[Dict[str, Any]]:
        """Get all seasons data.
        
        Returns:
            List[Dict[str, Any]]: List of season data dictionaries
        """
        try:
            seasons = []
            
            # Get all season identifiers
            season_ids = self.redis.smembers(self.ALL_SEASONS_KEY)
            
            for season_id in season_ids:
                # Parse season and year
                season_name, year = season_id.split(":")
                
                # Get season data
                season_key = self.SEASON_KEY_PATTERN.format(season=season_name, year=year)
                if self.redis.exists(season_key):
                    season_data = json.loads(self.redis.get(season_key))
                    seasons.append(season_data)
            
            # Sort seasons chronologically
            seasons = self._sort_seasons_chronologically(seasons)
            
            return seasons
            
        except Exception as e:
            self.logger.error(f"Error getting all seasons: {str(e)}")
            return []
            
    def _sort_seasons_chronologically(self, seasons: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort seasons chronologically by year and season."""
        from src.config.settings import config
        
        def season_sort_key(season):
            # Helper function to convert season name to a numeric value for sorting
            season_order = {
                "spring": 0,
                "summer": 1,
                "fall": 2, 
                "autumn": 2,  # Treat 'autumn' same as 'fall'
                "winter": 3,
                "resort": 4,
                "pre-fall": 5,
                "pre-spring": 6,
                "couture": 7
            }
            
            season_name = season.get("season", "").lower()
            year = season.get("year", "0")
            
            # Extract season from complex names (e.g., "Fall Ready-to-Wear" -> "fall")
            for key in season_order.keys():
                if key in season_name:
                    season_name = key
                    break
            
            # Get the numeric order or default to 99 (end of sort)
            season_num = season_order.get(season_name, 99)
            
            # Return a tuple of (year, season_number) for sorting
            return (int(year) if year.isdigit() else 0, season_num)
            
        # Sort seasons by year and season (using the config.sorting_type)
        return sorted(seasons, key=season_sort_key, reverse=(config.sorting_type.lower() == "desc"))
    
    def is_season_completed(self, season_data, year=None) -> bool:
        """Check if a season has been completely processed.
        
        Args:
            season_data: Either a dictionary with season info or season name string
            year: Season year (optional, required if season_data is a string)
            
        Returns:
            bool: True if season completed
        """
        try:
            # Handle both calling conventions for compatibility
            if isinstance(season_data, dict):
                season_name = season_data.get("season", "")
                year_value = season_data.get("year", "")
            else:
                # Original method signature case with separate year parameter
                season_name = season_data
                year_value = year
            
            if not season_name or not year_value:
                self.logger.error(f"Missing season or year in is_season_completed: {season_data}, {year}")
                return False
            
            season_result = self.get_season(season_name, year_value)
            if not season_result:
                return False
            
            return season_result.get("completed", False)
            
        except Exception as e:
            self.logger.error(f"Error checking season completion: {str(e)}")
            return False