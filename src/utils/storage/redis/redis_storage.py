"""Redis-based storage handler for Vogue scraper.

This module provides a Redis implementation for storing runway data,
offering improved performance and reliability compared to JSON storage.
"""

from typing import Dict, Any, Optional, List
import logging

from src.utils.storage.redis.redis_storage_base import RedisStorageBase
from src.utils.storage.redis.redis_storage_season import RedisStorageSeasonMixin
from src.utils.storage.redis.redis_storage_designer import RedisStorageDesignerMixin
from src.utils.storage.redis.redis_storage_look import RedisStorageLookMixin
from src.utils.storage.redis.redis_storage_compatibility import RedisStorageCompatibilityMixin
from src.utils.storage.redis.redis_storage_progress import RedisStorageProgressMixin
from src.exceptions.errors import StorageError


class RedisStorageHandler(
    RedisStorageBase,
    RedisStorageSeasonMixin,
    RedisStorageDesignerMixin,
    RedisStorageLookMixin,
    RedisStorageCompatibilityMixin,
    RedisStorageProgressMixin
):
    """Redis-based storage handler for runway data.
    
    This class combines functionality from multiple mixins to provide
    a complete storage solution using Redis as the backend.
    """
    
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
        # Initialize the base class
        super().__init__(host, port, db, password, checkpoint_id)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Redis storage handler initialized")