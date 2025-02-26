"""Checkpoint management for Vogue Runway scraper.

This module provides functionality for finding and managing checkpoints
across different storage backends (JSON and Redis).
"""

from typing import Optional
from pathlib import Path

from src.utils.logging import setup_logger
from src.config.settings import config

def find_latest_checkpoint() -> Optional[str]:
    """Find the most recent checkpoint file in the data directory or Redis.
    
    Returns either the latest JSON file or the latest Redis checkpoint ID
    depending on the storage mode.

    Returns:
        Optional[str]: Path to latest checkpoint file or Redis checkpoint ID or None if no checkpoints exist
    """
    try:
        logger = setup_logger()
        
        # For Redis storage
        if config.is_redis_storage:
            logger.info("Checking Redis for latest checkpoint")
            try:
                import redis
                
                # Connect to Redis
                redis_client = redis.Redis(
                    host=config.storage.REDIS.HOST,
                    port=config.storage.REDIS.PORT,
                    db=config.storage.REDIS.DB,
                    password=config.storage.REDIS.PASSWORD,
                    decode_responses=True
                )
                
                # Check if Redis is accessible
                if not redis_client.ping():
                    logger.error("Redis connection failed")
                    return None
                
                # Get metadata key where checkpoint info is stored
                metadata_key = "vogue:metadata"
                if not redis_client.exists(metadata_key):
                    logger.info("No Redis metadata found")
                    return None
                    
                # Get metadata and extract checkpoint ID
                metadata = redis_client.get(metadata_key)
                if metadata:
                    import json
                    try:
                        metadata_dict = json.loads(metadata)
                        # Look for instance_id or another identifier you're using
                        last_updated = metadata_dict.get("last_updated")
                        if last_updated:
                            logger.info(f"Found Redis checkpoint from {last_updated}")
                            # Return a special Redis checkpoint identifier that your code recognizes
                            return "redis:latest"  # Or a specific ID if you track them
                    except json.JSONDecodeError:
                        logger.error("Failed to parse Redis metadata")
                        
                logger.info("No valid Redis checkpoint found")
                return None
                
            except Exception as e:
                logger.error(f"Error checking Redis for checkpoint: {str(e)}")
                return None
        
        # For JSON storage, find the latest JSON file
        data_dir = Path(config.storage.BASE_DIR)
        if not data_dir.exists():
            return None

        json_files = list(data_dir.glob("*.json"))
        if not json_files:
            return None

        latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
        return str(latest_file)

    except Exception as e:
        logger = setup_logger()
        logger.error(f"Error finding latest checkpoint: {str(e)}")
        return None