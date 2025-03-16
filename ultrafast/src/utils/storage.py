"""
Redis storage utilities for the Ultrafast Vogue Scraper.

This module provides Redis-based storage for:
- Seasons and collections URLs
- Designer data
- Look images from all sections (Collection, Details, Beauty, etc.)
"""

import json
import redis
import logging
from typing import Dict, List, Any, Optional, Set, Union
from datetime import datetime
from redis.exceptions import RedisError


class RedisStorage:
    """Redis-based storage for the Ultrafast Vogue Scraper."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        prefix: str = "ultrafast:"
    ):
        """
        Initialize Redis storage connection.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (optional)
            prefix: Key prefix for all stored data
        """
        self.logger = logging.getLogger(__name__)
        self.prefix = prefix
        
        # Connect to Redis
        self.redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True
        )
        
        try:
            # Test connection
            self.redis.ping()
            self.logger.info(f"Connected to Redis at {host}:{port}/{db}")
        except RedisError as e:
            self.logger.error(f"Redis connection error: {str(e)}")
            raise
    
    def _key(self, name: str) -> str:
        """
        Create a prefixed Redis key.
        
        Args:
            name: Key name
            
        Returns:
            Prefixed key name
        """
        return f"{self.prefix}{name}"
    
    def store_seasons(self, seasons: List[Dict[str, str]]) -> bool:
        """
        Store list of seasons in Redis.
        
        Args:
            seasons: List of season dictionaries with 'season', 'year', and 'url'
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Store season URLs in a set
            season_urls = [season["url"] for season in seasons]
            self.redis.delete(self._key("seasons"))
            
            # Save each URL and store the list
            with self.redis.pipeline() as pipe:
                # Store each season as a hash
                for i, season in enumerate(seasons):
                    season_key = self._key(f"season:{i}")
                    pipe.hmset(season_key, season)
                
                # Store URLs in a list for ordering
                if season_urls:
                    pipe.rpush(self._key("seasons"), *season_urls)
                    
                # Store metadata
                pipe.set(self._key("metadata:seasons_count"), len(seasons))
                pipe.set(self._key("metadata:last_updated"), datetime.now().isoformat())
                pipe.execute()
            
            self.logger.info(f"Stored {len(seasons)} seasons in Redis")
            return True
            
        except RedisError as e:
            self.logger.error(f"Error storing seasons: {str(e)}")
            return False
    
    def store_season_collections(self, season_url: str, collections: List[Dict[str, str]]) -> bool:
        """
        Store collections for a specific season.
        
        Args:
            season_url: Season URL as the key
            collections: List of collection dictionaries with 'name' and 'url'
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create a safe key from the season URL
            season_key = self._key(f"collections:{self._safe_key(season_url)}")
            
            # Store collection URLs in a list for ordering
            collection_urls = [collection["url"] for collection in collections]
            
            with self.redis.pipeline() as pipe:
                # Delete existing data
                pipe.delete(season_key)
                
                # Store each collection as a hash
                for i, collection in enumerate(collections):
                    collection_key = self._key(f"collection:{self._safe_key(collection['url'])}")
                    pipe.hmset(collection_key, collection)
                
                # Store URLs in a list for ordering
                if collection_urls:
                    pipe.rpush(season_key, *collection_urls)
                    
                # Update metadata
                pipe.hincrby(self._key("metadata:progress"), "total_collections", len(collections))
                pipe.execute()
            
            self.logger.info(f"Stored {len(collections)} collections for season {season_url}")
            return True
            
        except RedisError as e:
            self.logger.error(f"Error storing collections: {str(e)}")
            return False
    
    def store_collection_looks(
        self,
        collection_url: str,
        sections: Dict[str, List[Dict[str, str]]]
    ) -> bool:
        """
        Store all look images from a collection grouped by section.
        
        Args:
            collection_url: Collection URL as the key
            sections: Dictionary mapping section names to lists of image data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create a safe key from the collection URL
            collection_key_base = self._key(f"looks:{self._safe_key(collection_url)}")
            
            with self.redis.pipeline() as pipe:
                # Store each section's looks
                total_looks = 0
                
                for section_name, looks in sections.items():
                    section_key = f"{collection_key_base}:{section_name}"
                    
                    # Store each look with its data
                    for i, look in enumerate(looks):
                        look_id = look.get("look_number", str(i+1))
                        look_key = f"{section_key}:{look_id}"
                        
                        # Store look data as a hash
                        pipe.hmset(look_key, {k: str(v) for k, v in look.items()})
                        
                        # Add to the section's look list
                        pipe.rpush(section_key, look_id)
                        
                    # Add section to collection's sections list
                    pipe.rpush(f"{collection_key_base}:sections", section_name)
                    total_looks += len(looks)
                
                # Update collection metadata
                pipe.hset(
                    self._key(f"collection:{self._safe_key(collection_url)}"),
                    "completed", "true"
                )
                
                # Update overall progress
                pipe.hincrby(self._key("metadata:progress"), "extracted_looks", total_looks)
                pipe.hincrby(self._key("metadata:progress"), "completed_collections", 1)
                
                # Execute all commands
                pipe.execute()
            
            self.logger.info(f"Stored {total_looks} looks across {len(sections)} sections for {collection_url}")
            return True
            
        except RedisError as e:
            self.logger.error(f"Error storing collection looks: {str(e)}")
            return False
    
    def get_seasons(self) -> List[Dict[str, str]]:
        """
        Get all stored seasons.
        
        Returns:
            List of season dictionaries
        """
        try:
            # Get season URLs from the list
            season_urls = self.redis.lrange(self._key("seasons"), 0, -1)
            seasons = []
            
            # Get each season's data
            for i, url in enumerate(season_urls):
                season_key = self._key(f"season:{i}")
                season_data = self.redis.hgetall(season_key)
                if season_data:
                    seasons.append(season_data)
            
            return seasons
            
        except RedisError as e:
            self.logger.error(f"Error getting seasons: {str(e)}")
            return []
    
    def get_collections(self, season_url: str) -> List[Dict[str, str]]:
        """
        Get all collections for a specific season.
        
        Args:
            season_url: Season URL
            
        Returns:
            List of collection dictionaries
        """
        try:
            # Get collection URLs from the list
            season_key = self._key(f"collections:{self._safe_key(season_url)}")
            collection_urls = self.redis.lrange(season_key, 0, -1)
            collections = []
            
            # Get each collection's data
            for url in collection_urls:
                collection_key = self._key(f"collection:{self._safe_key(url)}")
                collection_data = self.redis.hgetall(collection_key)
                if collection_data:
                    collections.append(collection_data)
            
            return collections
            
        except RedisError as e:
            self.logger.error(f"Error getting collections: {str(e)}")
            return []
    
    def get_collection_looks(self, collection_url: str) -> Dict[str, List[Dict[str, str]]]:
        """
        Get all looks for a specific collection grouped by section.
        
        Args:
            collection_url: Collection URL
            
        Returns:
            Dictionary mapping section names to lists of image data
        """
        try:
            # Create base key for the collection
            collection_key_base = self._key(f"looks:{self._safe_key(collection_url)}")
            
            # Get all sections for this collection
            sections_key = f"{collection_key_base}:sections"
            section_names = self.redis.lrange(sections_key, 0, -1)
            
            result = {}
            
            # Get looks for each section
            for section_name in section_names:
                section_key = f"{collection_key_base}:{section_name}"
                look_ids = self.redis.lrange(section_key, 0, -1)
                
                section_looks = []
                for look_id in look_ids:
                    look_key = f"{section_key}:{look_id}"
                    look_data = self.redis.hgetall(look_key)
                    if look_data:
                        section_looks.append(look_data)
                
                result[section_name] = section_looks
            
            return result
            
        except RedisError as e:
            self.logger.error(f"Error getting collection looks: {str(e)}")
            return {}
    
    def is_collection_completed(self, collection_url: str) -> bool:
        """
        Check if a collection has been fully processed.
        
        Args:
            collection_url: Collection URL
            
        Returns:
            True if collection is marked as completed
        """
        try:
            collection_key = self._key(f"collection:{self._safe_key(collection_url)}")
            completed = self.redis.hget(collection_key, "completed")
            return completed == "true"
            
        except RedisError:
            return False
    
    def get_progress(self) -> Dict[str, int]:
        """
        Get overall progress statistics.
        
        Returns:
            Dictionary with progress counters
        """
        try:
            progress_key = self._key("metadata:progress")
            progress_data = self.redis.hgetall(progress_key)
            
            # Convert string values to integers
            return {k: int(v) for k, v in progress_data.items()}
            
        except RedisError as e:
            self.logger.error(f"Error getting progress: {str(e)}")
            return {}
    
    def save_url_list(self, key: str, urls: List[str]) -> bool:
        """
        Save a list of URLs to a file-like Redis key.
        
        Args:
            key: Key name without prefix
            urls: List of URLs to save
            
        Returns:
            True if successful
        """
        try:
            full_key = self._key(key)
            
            # Delete existing key and write new content
            with self.redis.pipeline() as pipe:
                pipe.delete(full_key)
                
                if urls:
                    pipe.rpush(full_key, *urls)
                    
                pipe.execute()
            
            return True
            
        except RedisError as e:
            self.logger.error(f"Error saving URL list: {str(e)}")
            return False
    
    def _safe_key(self, url: str) -> str:
        """
        Convert URL to a Redis-safe key string.
        
        Args:
            url: URL to convert
            
        Returns:
            Safe key string
        """
        return url.replace("https://", "").replace("http://", "").replace("/", "_")