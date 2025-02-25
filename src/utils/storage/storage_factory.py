# utils/storage/storage_factory.py
"""Factory for creating storage handlers.

This module provides a factory for creating either Redis or JSON storage handlers
based on configuration settings.
"""

import logging
from typing import Optional, Any

from src.config.settings import config
from src.exceptions.errors import StorageError
from src.utils.storage.storage_handler import DataStorageHandler
from src.utils.storage.redis_storage import RedisStorageHandler


class StorageFactory:
    """Factory class for creating storage handlers."""

    @staticmethod
    def create_storage_handler(checkpoint: Optional[str] = None) -> Any:
        """Create and return a storage handler based on configuration.
        
        Args:
            checkpoint: Optional checkpoint file/ID to resume from
            
        Returns:
            Storage handler instance (JSON or Redis)
            
        Raises:
            StorageError: If storage mode is invalid
        """
        logger = logging.getLogger(__name__)
        
        if config.is_redis_storage:
            logger.info("Using Redis storage handler")
            return RedisStorageHandler(
                host=config.storage.REDIS.HOST,
                port=config.storage.REDIS.PORT,
                db=config.storage.REDIS.DB,
                password=config.storage.REDIS.PASSWORD,
                checkpoint_id=checkpoint
            )
        elif config.storage.STORAGE_MODE.lower() == "json":
            logger.info("Using JSON storage handler")
            return DataStorageHandler(
                base_dir=config.storage.BASE_DIR,
                checkpoint_file=checkpoint
            )
        else:
            error_msg = f"Invalid storage mode: {config.storage.STORAGE_MODE}"
            logger.error(error_msg)
            raise StorageError(error_msg)