"""Main entry point for Vogue Runway scraper with real-time storage.

This module contains the main scraper orchestrator that coordinates between
the web scraper, storage handler, and various components to collect and store
runway show data in real-time with automatic checkpoint management.
"""

import argparse
import os
import sys
from typing import Dict, Optional, List, Tuple, Any
from datetime import datetime
from pathlib import Path

from src.scraper import VogueScraper
from src.utils.driver import setup_chrome_driver
from src.utils.logging import setup_logger
from src.utils.storage.storage_factory import StorageFactory
from src.config.settings import config, BASE_URL, AUTH_URL
from src.exceptions.errors import AuthenticationError, ScraperError, StorageError
from src.handlers.slideshow import VogueSlideshowScraper
from src.utils.storage.progress_tracker import ProgressTracker


def find_latest_checkpoint() -> Optional[str]:
    """Find the most recent checkpoint file in the data directory.
    
    Returns either the latest JSON file or the latest Redis checkpoint ID
    depending on the storage mode.

    Returns:
        Optional[str]: Path to latest checkpoint file or None if no checkpoints exist
    """
    try:
        logger = setup_logger()
        
        # For Redis storage, we would need a different approach
        if config.is_redis_storage:
            # In a real implementation, we would query Redis for the latest checkpoint ID
            # This is a simplified placeholder
            logger.info("Redis storage mode - checkpoint auto-detection not implemented")
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


class VogueRunwayScraper:
    """Main scraper orchestrator class with real-time data storage."""

    def __init__(self, checkpoint_file: Optional[str] = None):
        """Initialize the scraper orchestrator.

        Args:
            checkpoint_file: Optional path to checkpoint file or ID to resume from
        """
        self.logger = setup_logger()

        # If no checkpoint file is provided, try to find the latest one
        if checkpoint_file is None:
            latest_checkpoint = find_latest_checkpoint()
            if latest_checkpoint:
                self.logger.info(f"Using latest checkpoint: {latest_checkpoint}")
                checkpoint_file = latest_checkpoint
            else:
                self.logger.info("No existing checkpoint found, starting fresh")

        # Create storage handler using factory based on configuration
        self.storage = StorageFactory.create_storage_handler(checkpoint_file)
        self.logger.info(f"Using {config.storage.STORAGE_MODE} storage")
        
        self.driver = None
        self.scraper = None
        self.current_file = None

    def initialize_scraper(self) -> None:
        """Initialize the Selenium driver and VogueScraper.

        Raises:
            ScraperError: If initialization fails
        """
        try:
            self.driver = setup_chrome_driver()
            self.scraper = VogueScraper(
                driver=self.driver,
                logger=self.logger,
                storage_handler=self.storage,
                base_url=BASE_URL,
            )
            self.logger.info("Scraper initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize scraper: {str(e)}")
            raise ScraperError(f"Scraper initialization failed: {str(e)}")

    def validate_storage(self) -> bool:
        """Validate storage state and data integrity.

        Returns:
            bool: True if storage is valid and ready for use
        """
        try:
            if not self.storage or not self.storage.exists():
                self.logger.error("Storage not initialized")
                return False

            validation = self.storage.validate()
            if not validation["valid"]:
                self.logger.error(
                    f"Storage validation failed: {validation.get('error', 'Unknown error')}"
                )
                return False

            status = self.storage.get_status()
            if not status:
                self.logger.error("Could not get storage status")
                return False

            self.logger.info("Storage validation successful")
            return True

        except Exception as e:
            self.logger.error(f"Storage validation error: {str(e)}")
            return False

    def _get_season_index(self, season: Dict[str, str]) -> Optional[int]:
        """Get index of season in storage or None if not found.

        Args:
            season: Season data containing season and year

        Returns:
            Index of the season or None if not found
        """
        try:
            if not self.current_file:
                return None

            current_data = self.storage.read_data()
            for i, stored_season in enumerate(current_data["seasons"]):
                if (
                    stored_season["season"] == season["season"]
                    and stored_season["year"] == season["year"]
                ):
                    return i
            return None
        except StorageError as e:
            self.logger.error(f"Error getting season index: {str(e)}")
            return None

    def process_season(self, season: Dict[str, str]) -> None:
        """Process a single season's data with real-time storage."""
        self.logger.info(f"Processing season: {season['season']} {season['year']}")

        try:
            # Check if season exists and initialize if needed
            season_index = self._get_season_index(season)
            if season_index is None:
                self.storage.update_data(
                    season_data={
                        "season": season["season"],
                        "year": season["year"],
                        "url": season["url"],
                        "designers": [],
                        "total_designers": 0,
                        "completed_designers": 0,
                    }
                )
                season_index = self._get_season_index(season)
                if season_index is None:
                    raise ScraperError("Failed to initialize season data")

            # Check if season is already completed
            if not self.storage.is_season_completed(season):
                self.logger.info(f"Fetching designers for season: {season['url']}")
                designers = self.scraper.get_designers_for_season(season["url"])
                self.logger.info(f"Total designers found: {len(designers)}")

                # Initialize slideshow scraper and progress tracker
                slideshow_scraper = VogueSlideshowScraper(self.driver, self.logger, self.storage)
                progress_tracker = ProgressTracker(self.storage, self.logger)

                for designer_index, designer in enumerate(designers):
                    # Reset session state at start of each iteration
                    active_session = False

                    try:
                        # Skip if designer is already completed
                        if self.storage.is_designer_completed(designer["url"]):
                            self.logger.info(f"Designer already completed: {designer['name']}")
                            continue

                        # Start designer session
                        self.logger.info(f"Starting session for designer: {designer['name']}")
                        self.storage._start_designer_session(designer["url"])
                        active_session = True

                        # Update designer data
                        designer_data = {
                            "season_index": season_index,
                            "designer_index": designer_index,
                            "data": {
                                "name": designer["name"],
                                "url": designer["url"],
                                "looks": [],
                            },
                            "total_looks": 0,
                            "extracted_looks": 0,  # Initialize extracted looks counter
                        }

                        success = self.storage.update_data(designer_data=designer_data)
                        if not success:
                            self.logger.error(
                                f"Failed to update data for designer: {designer['name']}"
                            )
                            raise Exception("Failed to update designer data")

                        # Scrape the designer's slideshow
                        success = slideshow_scraper.scrape_designer_slideshow(
                            designer["url"],
                            season_index,
                            designer_index,
                            progress_tracker,  # Pass progress tracker to slideshow scraper
                        )

                        if not success:
                            self.logger.error(f"Failed to scrape slideshow for: {designer['name']}")
                            raise Exception("Failed to scrape designer slideshow")

                        # End designer session
                        if active_session:
                            self.storage._end_designer_session()
                            active_session = False

                        # Update progress and save
                        progress_tracker.update_overall_progress()
                        self.storage.save_progress()
                        self.logger.info(f"Completed processing designer: {designer['name']}")

                    except Exception as e:
                        self.logger.error(f"Error processing designer {designer['name']}: {str(e)}")
                        if active_session:
                            self.storage._end_designer_session()
                        continue

            else:
                self.logger.info(f"Season already completed: {season['season']} {season['year']}")

        except Exception as e:
            self.logger.error(
                f"Error processing season {season['season']} {season['year']}: {str(e)}"
            )
            if hasattr(self.storage, "_active_session") and self.storage._active_session:
                self.storage._end_designer_session()
            raise ScraperError(f"Season processing failed: {str(e)}")

    def resume_from_checkpoint(self) -> Tuple[Optional[int], Optional[Dict[str, Any]]]:
        """Resume scraping from last checkpoint in storage.

        Returns:
            Tuple of (season_index, season_data) or (None, None) if no checkpoint
        """
        try:
            current_data = self.storage.read_data()

            # Find first incomplete season
            for season_index, season in enumerate(current_data["seasons"]):
                if not season.get("completed", False):
                    self.logger.info(f"Resuming from season: {season['season']} {season['year']}")
                    return season_index, season

            # All seasons completed
            self.logger.info("All seasons completed, no checkpoint needed")
            return None, None

        except Exception as e:
            self.logger.error(f"Error reading checkpoint: {str(e)}")
            return None, None

    def run(self) -> None:
        """Execute the main scraping process with real-time storage.

        This method coordinates the entire scraping process, including:
        - Storage initialization and validation
        - Scraper setup and authentication
        - Automatic checkpoint management
        - Season processing
        - Progress tracking and error handling
        """
        self.logger.info("=== Starting Vogue Scraper ===")

        try:
            # Initialize storage
            self.current_file = self.storage.initialize_file()

            # Validate storage state
            if not self.validate_storage():
                raise StorageError("Storage validation failed")

            # Initialize scraper and authenticate
            self.initialize_scraper()
            if not self.scraper.authenticate(AUTH_URL):
                raise AuthenticationError("Failed to authenticate with Vogue")

            # Check for existing progress
            checkpoint = self.resume_from_checkpoint()
            if checkpoint[0] is not None:
                start_index = checkpoint[0]
                self.logger.info("Resuming from previous checkpoint")
            else:
                start_index = 0
                # Get all seasons if starting fresh
                seasons = self.scraper.get_seasons_list()
                if not seasons:
                    self.logger.error("No seasons found")
                    return

                self.logger.info(f"Found {len(seasons)} seasons")

                # Save all season metadata
                for season in seasons:
                    # Additional filter to avoid non-fashion show/article pages
                    if not any(word in season["season"] for word in ["MORE FROM", "SEE MORE", "ARTICLE", "BLOG"]):
                        # Skip URLs that appear to be articles
                        if "/article/" in season["url"]:
                            self.logger.info(f"Skipping article URL: {season['url']}")
                            continue
                        self.storage.update_data(season_data=season)

            # Process seasons from checkpoint
            current_data = self.storage.read_data()
            for season_index in range(start_index, len(current_data["seasons"])):
                try:
                    season = current_data["seasons"][season_index]
                    self.process_season(season)
                    # Save progress after each season
                    self.storage.save_progress()
                except ScraperError as e:
                    self.logger.error(str(e))
                    continue

        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")

        finally:
            if self.driver:
                self.driver.quit()

            # Save final progress
            if self.storage and hasattr(self.storage, "save_progress"):
                self.storage.save_progress()

            # Log final status if possible
            try:
                if self.storage:
                    status = self.storage.get_status()
                    if status and status.get("progress"):
                        self.logger.info(f"Final progress: {status['progress']}")
            except Exception as e:
                self.logger.error(f"Error logging final status: {str(e)}")

        self.logger.info("=== Vogue Scraper Complete ===")


def main():
    """Main entry point with automatic checkpoint detection."""
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

    # Create data directory if it doesn't exist
    data_dir = Path(config.storage.BASE_DIR)
    data_dir.mkdir(exist_ok=True)

    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Initialize and run scraper
    scraper = VogueRunwayScraper(checkpoint_file=args.checkpoint)
    scraper.run()


if __name__ == "__main__":
    main()
