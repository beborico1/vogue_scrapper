"""Redis-based storage handler for Vogue scraper.

This module provides a Redis implementation for storing runway data,
offering improved performance and reliability compared to JSON storage.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import redis
from pathlib import Path

from src.utils.storage.models import (
    Image, Look, Designer, Season, Progress, Metadata
)
from src.exceptions.errors import StorageError


class RedisStorageHandler:
    """Redis-based storage handler for runway data."""

    # Key patterns
    METADATA_KEY = "vogue:metadata"
    SEASON_KEY_PATTERN = "vogue:season:{season}:{year}"
    DESIGNER_KEY_PATTERN = "vogue:designer:{url}"
    LOOK_KEY_PATTERN = "vogue:look:{designer_url}:{look_number}"
    ALL_SEASONS_KEY = "vogue:seasons"
    ALL_DESIGNERS_KEY = "vogue:designers"
    
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, 
                 password: Optional[str] = None, checkpoint_id: Optional[str] = None):
        """Initialize Redis storage handler."""
        self.logger = logging.getLogger(__name__)
        self._current_temp_file = None
        
        try:
            self.redis = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True  # Always decode to strings
            )
            self.logger.info(f"Connected to Redis at {host}:{port}/db{db}")
            
            # Ping to verify connection
            self.redis.ping()
            
            # Initialize or load checkpoint
            if checkpoint_id:
                self.instance_id = checkpoint_id
                self.logger.info(f"Using existing checkpoint ID: {checkpoint_id}")
            else:
                # Generate new instance ID with timestamp
                self.instance_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.logger.info(f"Created new instance ID: {self.instance_id}")
                
                # Initialize metadata
                if not self.redis.exists(self.METADATA_KEY):
                    self._initialize_metadata()
            
        except redis.ConnectionError as e:
            self.logger.error(f"Failed to connect to Redis: {str(e)}")
            raise StorageError(f"Redis connection failed: {str(e)}")
    
    def _initialize_metadata(self) -> None:
        """Initialize metadata structure in Redis."""
        metadata = Metadata()
        self.redis.set(self.METADATA_KEY, json.dumps(metadata.to_dict()))
        self.logger.info("Initialized Redis metadata")
        
    def initialize_file(self) -> str:
        """Initialize Redis storage (for compatibility with JSON storage interface)."""
        # Check if metadata exists, if not initialize it
        if not self.redis.exists(self.METADATA_KEY):
            self._initialize_metadata()
            
        self.logger.info(f"Initialized Redis storage with ID: {self.instance_id}")
        return self.instance_id
    
    def add_season(self, season_data: Dict[str, Any]) -> bool:
        """Add or update season data."""
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
    
    def add_designer(self, designer_data: Dict[str, Any], season: str, year: str) -> bool:
        """Add or update designer data."""
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
    
    def add_look(self, designer_url: str, look_number: int, images: List[Dict[str, Any]]) -> bool:
        """Add or update look data."""
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
            
            # Current problematic code:
            look.images.extend(processed_images)
            look.completed = True

            # Replace with this:
            # Check for duplicate images before adding
            if look_exists:
                # Replace images entirely to avoid duplicates
                look.images = processed_images
            else:
                # For new looks, simply set the images
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
            
            # Update metadata
            self._update_metadata_progress()
            
            self.logger.info(f"Saved look {look_number} with {len(processed_images)} images. Designer has {designer.extracted_looks}/{designer.total_looks} looks completed.")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding look: {str(e)}")
            return False
    
    def get_season(self, season: str, year: str) -> Optional[Dict[str, Any]]:
        """Get season data by season name and year."""
        try:
            season_key = self.SEASON_KEY_PATTERN.format(season=season, year=year)
            
            if not self.redis.exists(season_key):
                return None
            
            season_data = json.loads(self.redis.get(season_key))
            return season_data
            
        except Exception as e:
            self.logger.error(f"Error getting season: {str(e)}")
            return None
    
    def get_designer(self, designer_url: str) -> Optional[Dict[str, Any]]:
        """Get designer data by URL."""
        try:
            designer_key = self.DESIGNER_KEY_PATTERN.format(url=designer_url)
            
            if not self.redis.exists(designer_key):
                return None
            
            designer_data = json.loads(self.redis.get(designer_key))
            return designer_data
            
        except Exception as e:
            self.logger.error(f"Error getting designer: {str(e)}")
            return None
    
    def get_look(self, designer_url: str, look_number: int) -> Optional[Dict[str, Any]]:
        """Get look data by designer URL and look number."""
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
    
    def get_all_seasons(self) -> List[Dict[str, Any]]:
        """Get all seasons data."""
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
            
        # Sort seasons by year and season (oldest first)
        return sorted(seasons, key=season_sort_key)
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata."""
        try:
            if not self.redis.exists(self.METADATA_KEY):
                self._initialize_metadata()
            
            metadata = json.loads(self.redis.get(self.METADATA_KEY))
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error getting metadata: {str(e)}")
            return {}
    
    def is_season_completed(self, season_data, year=None) -> bool:
        """Check if a season has been completely processed."""
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
    
    def is_designer_completed(self, designer_url: str) -> bool:
        """Check if a designer's show has been completely processed."""
        try:
            designer_data = self.get_designer(designer_url)
            if not designer_data:
                return False
            
            return designer_data.get("completed", False)
            
        except Exception as e:
            self.logger.error(f"Error checking designer completion: {str(e)}")
            return False
    
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
                    
                    # Convert designer data to Designer object
                    designer_obj = Designer.from_dict(designer_data)
                    
                    # Count completed looks properly using the actual Designer object
                    completed_look_count = sum(1 for look in designer_obj.looks if look.completed and look.images)
                    
                    # Log both counts for comparison
                    self.logger.info(f"Designer {designer_name}: extracted_looks={designer_data.get('extracted_looks', 0)}, counted_looks={completed_look_count}")
                    
                    # Update the designer's extracted_looks in Redis if different
                    if designer_obj.extracted_looks != completed_look_count:
                        self.logger.info(f"Updating extracted_looks for {designer_name}: {designer_obj.extracted_looks} -> {completed_look_count}")
                        designer_obj.extracted_looks = completed_look_count
                        designer_obj.completed = completed_look_count >= design_total_looks
                        self.redis.set(designer_key, json.dumps(designer_obj.to_dict()))
                    
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
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scraping status and progress."""
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
    
    def save_progress(self) -> None:
        """Save current progress (compatibility method)."""
        # In Redis, progress is saved in real-time, so we just update metadata
        try:
            self._update_metadata_progress()
            self.logger.info("Progress saved")
        except Exception as e:
            self.logger.error(f"Error saving progress: {str(e)}")
    
    def validate(self) -> Dict[str, Any]:
        """Validate storage state (compatibility method)."""
        try:
            # Check if metadata exists
            if not self.redis.exists(self.METADATA_KEY):
                return {"valid": False, "error": "Metadata not found"}
            
            # Check connection
            self.redis.ping()
            
            return {"valid": True}
        except Exception as e:
            self.logger.error(f"Validation error: {str(e)}")
            return {"valid": False, "error": str(e)}
    
    def read_data(self) -> Dict[str, Any]:
        """Read current data (compatibility method)."""
        try:
            return {
                "metadata": self.get_metadata(),
                "seasons": self.get_all_seasons()
            }
        except Exception as e:
            self.logger.error(f"Error reading data: {str(e)}")
            return {"metadata": {}, "seasons": []}
        
    def write_data(self, data: Dict[str, Any]) -> None:
        """Write data (compatibility method)."""
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
    
    def exists(self) -> bool:
        """Check if storage exists (compatibility method)."""
        try:
            return self.redis.exists(self.METADATA_KEY) > 0
        except Exception as e:
            self.logger.error(f"Error checking existence: {str(e)}")
            return False
    
    def update_data(self, season_data: Optional[Dict[str, Any]] = None,
                    designer_data: Optional[Dict[str, Any]] = None,
                    look_data: Optional[Dict[str, Any]] = None) -> bool:
        """Update data (compatibility method)."""
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
    
    def _start_designer_session(self, designer_url: str) -> None:
        """Start a designer session (compatibility method)."""
        self.logger.info(f"Started session for designer: {designer_url}")
    
    def _end_designer_session(self) -> None:
        """End a designer session (compatibility method)."""
        self.logger.info("Ended designer session")
        
    def get_current_file(self) -> Optional[Path]:
        """Get current file path (compatibility method).
        
        For Redis, we don't have a file, so we create a temporary one with
        current data for compatibility with scripts that expect files.
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
    
    def update_look_data(self, season_index: int, designer_index: int, look_number: int, images: List[Dict[str, Any]]) -> bool:
        """Update look data (compatibility method)."""
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