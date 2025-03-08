"""Main entry point for Vogue Runway scraper with parallel processing.

This module contains the main script entry point that parses command line arguments
and initializes the scraper orchestrator.
"""

import argparse
import os
import sys
from pathlib import Path

from src.scraper_orchestrator import VogueRunwayScraper
from src.checkpoint_manager import find_latest_checkpoint
from src.config.settings import config


def main():
    """Main entry point with parallel processing support."""
    parser = argparse.ArgumentParser(description="Vogue Runway Scraper")
    parser.add_argument(
        "--checkpoint", "-c",
        type=str,
        help="Path to checkpoint file or ID to resume from (optional, will use latest if not specified)",
    )
    parser.add_argument(
        "--storage", "-s",
        type=str,
        choices=["json", "redis"],
        help="Storage backend to use (json or redis)",
    )
    parser.add_argument(
        "--redis-host", 
        type=str,
        help="Redis host (default: localhost)",
    )
    parser.add_argument(
        "--redis-port", 
        type=int,
        help="Redis port (default: 6379)",
    )
    parser.add_argument(
        "--redis-db", 
        type=int,
        help="Redis database number (default: 0)",
    )
    parser.add_argument(
        "--redis-password", 
        type=str,
        help="Redis password (if required)",
    )
    
    # Add sorting type parameter
    parser.add_argument(
        "--sort", 
        type=str,
        choices=["asc", "desc"],
        help="Season sorting order: 'asc' for oldest first, 'desc' for newest first (default: desc)",
    )
    
    # Add parallel processing arguments
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Enable parallel processing",
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)",
    )
    parser.add_argument(
        "--mode", "-m",
        type=str,
        choices=["multi-season", "multi-designer", "multi-look"],
        default="multi-designer",
        help="Parallelization mode (default: multi-designer)",
    )
    
    args = parser.parse_args()

    # Override config from command line args
    if args.storage:
        config.storage.STORAGE_MODE = args.storage
        
    if args.redis_host:
        config.storage.REDIS.HOST = args.redis_host
        
    if args.redis_port:
        config.storage.REDIS.PORT = args.redis_port
        
    if args.redis_db:
        config.storage.REDIS.DB = args.redis_db
        
    if args.redis_password:
        config.storage.REDIS.PASSWORD = args.redis_password
        
    # Set sorting type if specified
    if args.sort:
        config.sorting_type = args.sort

    # Create data directory if it doesn't exist
    data_dir = Path(config.storage.BASE_DIR)
    data_dir.mkdir(exist_ok=True)

    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Initialize and run scraper with parallel processing if requested
    scraper = VogueRunwayScraper(
        checkpoint_file=args.checkpoint,
        parallel=args.parallel,
        parallel_mode=args.mode,
        max_workers=args.workers
    )
    scraper.run()


if __name__ == "__main__":
    main()