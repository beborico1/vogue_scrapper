#!/usr/bin/env python
"""
Ultrafast Vogue Scraper

This is an optimized version of the Vogue scraper designed for maximum speed.
It directly accesses collection pages and extracts all sections (Collection, Details, Beauty, etc.)
by using the "Load More" buttons to expand content before extraction.

Features:
- Non-headless browser for visual monitoring
- Authentication compatible with main scraper
- Redis storage for performance
- Parallel processing
- Direct collection page access
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path for shared imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ultrafast.src.config.settings import Config
from ultrafast.src.scraper import UltrafastVogueScraper


def setup_logging(log_file=None):
    """Set up logging configuration.
    
    Args:
        log_file: Path to log file, if None will use default in data directory
    """
    # Get ultrafast directory and data directory
    ultrafast_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(ultrafast_dir, "data")
    
    # If log_file is None, use default path
    if log_file is None:
        log_file = os.path.join(data_dir, "scraper.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("UltrafastVogueScraper")


def main():
    """Main entry point for the ultrafast scraper."""
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Ultrafast Vogue Scraper")
    parser.add_argument(
        "--redis-host", 
        type=str,
        default="localhost",
        help="Redis host (default: localhost)",
    )
    parser.add_argument(
        "--redis-port", 
        type=int,
        default=6379,
        help="Redis port (default: 6379)",
    )
    parser.add_argument(
        "--redis-db", 
        type=int,
        default=0,
        help="Redis database number (default: 0)",
    )
    parser.add_argument(
        "--redis-password", 
        type=str,
        help="Redis password (if required)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of workers for parallel processing (default: 4)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previously stored data",
    )
    parser.add_argument(
        "--use-static-seasons",
        action="store_true",
        help="Use statically generated seasons list instead of scraping",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Process collections sequentially (no parallel processing)",
    )
    
    args = parser.parse_args()
    
    # Ensure data directory exists
    ultrafast_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(ultrafast_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    # Set up logging
    logger = setup_logging()
    logger.info("Starting Ultrafast Vogue Scraper")
    
    # Initialize configuration
    config = Config(
        redis_host=args.redis_host,
        redis_port=args.redis_port,
        redis_db=args.redis_db,
        redis_password=args.redis_password,
        workers=args.workers
    )
    
    # Set correct data directory
    ultrafast_dir = os.path.dirname(os.path.abspath(__file__))
    config.data_dir = os.path.join(ultrafast_dir, "data")
    
    # Initialize and run scraper
    scraper = UltrafastVogueScraper(
        config, 
        logger, 
        resume=args.resume, 
        use_static_seasons=args.use_static_seasons,
        sequential=args.sequential
    )
    scraper.run()


if __name__ == "__main__":
    main()