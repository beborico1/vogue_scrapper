"""Redis-based storage handler base class.

This module provides the base Redis implementation for storing runway data,
with core connection handling and utility methods.
"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
import redis

from src.utils.storage.models import Progress, Metadata
from src.exceptions.errors import StorageError


class RedisStorageBase:
    """Base class for Redis-based storage handler."""

    # Key patterns
    METADATA_KEY = "vogue:metadata"
    SEASON_KEY_PATTERN = "vogue:season:{season}:{year}"
    DESIGNER_KEY_PATTERN = "vogue:designer:{url}"
    LOOK_KEY_PATTERN = "vogue:look:{designer_url}:{look_number}"
    ALL_SEASONS_KEY = "vogue:seasons"
    ALL_DESIGNERS_KEY = "vogue:designers"
    
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, 
                password: Optional[str] = None, checkpoint_id: Optional[str] = None):
        """Initialize Redis storage handler.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Optional Redis password
            checkpoint_id: Optional checkpoint ID to resume from
        """
        self.logger = logging.getLogger(__name__)
        self._current_temp_file = None
        
        try:
            self.redis = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True
            )
            self.logger.info(f"Connected to Redis at {host}:{port}/db{db}")
            
            # Ping to verify connection
            self.redis.ping()
            
            # Initialize or load checkpoint
            if checkpoint_id and checkpoint_id != "latest":
                # Use specific checkpoint ID
                self.instance_id = checkpoint_id
                self.logger.info(f"Using specific checkpoint ID: {checkpoint_id}")
            else:
                # For 'latest' or None, try to get the latest instance from metadata
                metadata_key = "vogue:metadata"
                if self.redis.exists(metadata_key):
                    try:
                        metadata = json.loads(self.redis.get(metadata_key))
                        last_instance = metadata.get("instance_id")
                        if last_instance:
                            self.instance_id = last_instance
                            self.logger.info(f"Using latest instance ID from metadata: {last_instance}")
                        else:
                            # Create new instance if none found
                            self.instance_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                            self.logger.info(f"Created new instance ID: {self.instance_id}")
                    except:
                        # Create new instance if metadata parsing fails
                        self.instance_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                        self.logger.info(f"Created new instance ID: {self.instance_id}")
                else:
                    # Create new instance if no metadata exists
                    self.instance_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                    self.logger.info(f"Created new instance ID: {self.instance_id}")
                    
                    # Initialize metadata
                    self._initialize_metadata()
        except redis.ConnectionError as e:
            self.logger.error(f"Failed to connect to Redis: {str(e)}")
            raise StorageError(f"Redis connection failed: {str(e)}")
        
    def _initialize_metadata(self) -> None:
        """Initialize metadata structure in Redis."""
        metadata = {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "instance_id": self.instance_id,  # Store the instance ID
            "overall_progress": {
                "total_seasons": 0,
                "completed_seasons": 0,
                "total_designers": 0,
                "completed_designers": 0,
                "total_looks": 0,
                "extracted_looks": 0,
                "start_time": datetime.now().isoformat()
            }
        }
        self.redis.set("vogue:metadata", json.dumps(metadata))
        self.logger.info("Initialized Redis metadata")
        
    def initialize_file(self) -> str:
        """Initialize Redis storage (for compatibility with JSON storage interface)."""
        # Check if metadata exists, if not initialize it
        if not self.redis.exists(self.METADATA_KEY):
            self._initialize_metadata()
            
        self.logger.info(f"Initialized Redis storage with ID: {self.instance_id}")
        return self.instance_id
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata from Redis."""
        try:
            if not self.redis.exists(self.METADATA_KEY):
                self._initialize_metadata()
            
            metadata = json.loads(self.redis.get(self.METADATA_KEY))
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error getting metadata: {str(e)}")
            return {}
    
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
    
    def exists(self) -> bool:
        """Check if storage exists."""
        try:
            return self.redis.exists(self.METADATA_KEY) > 0
        except Exception as e:
            self.logger.error(f"Error checking existence: {str(e)}")
            return False
            
    def _update_metadata_progress(self) -> None:
        """Abstract method to update metadata progress.
        
        This should be implemented in a derived class.
        """
        raise NotImplementedError("This method should be implemented in a derived class")
        
    def _start_designer_session(self, designer_url: str) -> None:
        """Start a designer session (compatibility method)."""
        self.logger.info(f"Started session for designer: {designer_url}")
    
    def _end_designer_session(self) -> None:
        """End a designer session (compatibility method)."""
        self.logger.info("Ended designer session")

    def _update_metadata_progress(self) -> None:
        """Update metadata with current progress statistics."""
        try:
            # Get current metadata
            metadata_str = self.redis.get(self.METADATA_KEY)
            if not metadata_str:
                self._initialize_metadata()
                metadata_str = self.redis.get(self.METADATA_KEY)
            
            metadata = json.loads(metadata_str)
            
            # Update last_updated
            metadata["last_updated"] = datetime.now().isoformat()
            
            # Calculate progress statistics
            all_seasons = self.get_all_seasons()
            seasons_count = len(all_seasons)
            completed_seasons = sum(1 for s in all_seasons if s.get("completed", False))
            
            designers_count = self.redis.scard(self.ALL_DESIGNERS_KEY)
            completed_designers = 0
            total_looks = 0
            extracted_looks = 0
            
            # Count completed designers and looks
            for designer_url in self.redis.smembers(self.ALL_DESIGNERS_KEY):
                designer_key = self.DESIGNER_KEY_PATTERN.format(url=designer_url)
                if self.redis.exists(designer_key):
                    designer_data = json.loads(self.redis.get(designer_key))
                    
                    # Count completed designer
                    if designer_data.get("completed", False):
                        completed_designers += 1
                    
                    # Get total looks
                    design_total_looks = designer_data.get("total_looks", 0)
                    total_looks += design_total_looks
                    
                    # Get completed look count
                    completed_look_count = designer_data.get("extracted_looks", 0)
                    extracted_looks += completed_look_count
            
            # Calculate completion percentage
            completion_percentage = 0.0
            if total_looks > 0:
                completion_percentage = round((extracted_looks / total_looks) * 100, 2)
            
            # Update progress in metadata
            if "overall_progress" not in metadata:
                metadata["overall_progress"] = {}
                
            progress = metadata["overall_progress"]
            progress.update({
                "total_seasons": seasons_count,
                "completed_seasons": completed_seasons,
                "total_designers": designers_count,
                "completed_designers": completed_designers,
                "total_looks": total_looks,
                "extracted_looks": extracted_looks,
                "completion_percentage": completion_percentage,
                "last_updated": datetime.now().isoformat()
            })
            
            # Save updated metadata
            self.redis.set(self.METADATA_KEY, json.dumps(metadata))
            
        except Exception as e:
            self.logger.error(f"Error updating metadata progress: {str(e)}")