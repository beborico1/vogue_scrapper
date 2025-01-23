"""Main entry point for Vogue Runway scraper with real-time storage.

This module contains the main scraper orchestrator that coordinates between
the web scraper, storage handler, and various components to collect and store
runway show data in real-time.
"""

import argparse
from typing import Dict, Optional, List, Tuple, Any
from pathlib import Path

from src.scraper import VogueScraper
from src.utils.driver import setup_chrome_driver
from src.utils.logging import setup_logger
from src.utils.storage.storage_handler import DataStorageHandler
from src.config.settings import BASE_URL, AUTH_URL
from src.exceptions.errors import AuthenticationError, ScraperError, StorageError


class VogueRunwayScraper:
    """Main scraper orchestrator class with real-time data storage."""

    def __init__(self, checkpoint_file: Optional[str] = None):
        """Initialize the scraper orchestrator.

        Args:
            checkpoint_file: Optional path to checkpoint file to resume from
        """
        self.logger = setup_logger()
        self.storage = DataStorageHandler(checkpoint_file=checkpoint_file)
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
            True if storage is valid and ready for use
        """
        try:
            # First check if storage exists
            if not self.storage or not self.storage.exists():
                self.logger.error("Storage not initialized")
                return False

            # Get validation results
            validation = self.storage.validate()
            if not validation["valid"]:
                self.logger.error(
                    f"Storage validation failed: {validation.get('error', 'Unknown error')}"
                )
                return False

            # Get current status to verify data
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
        """Process a single season's data with real-time storage.

        Args:
            season: Season data to process

        Raises:
            ScraperError: If season processing fails
        """
        self.logger.info(f"Processing season: {season['season']} {season['year']}")

        try:
            # Check if season exists in storage
            season_index = self._get_season_index(season)
            if season_index is None:
                # Save initial season data
                self.storage.update_data(
                    season_data={
                        "season": season["season"],
                        "year": season["year"],
                        "url": season["url"],
                    }
                )
                season_index = len(self.storage.read_data()["seasons"]) - 1

            # Check if season is already completed
            if not self.storage.is_season_completed(season):
                designers = self.scraper.get_designers_for_season(season["url"])

                for designer_index, designer in enumerate(designers):
                    try:
                        # Skip if designer is already completed
                        if self.storage.is_designer_completed(designer["url"]):
                            self.logger.info(f"Designer already completed: {designer['name']}")
                            continue

                        # Get slideshow URL
                        slideshow_url = self.scraper.get_slideshow_url(designer["url"])
                        if not slideshow_url:
                            self.logger.warning(
                                f"No slideshow found for designer: {designer['name']}"
                            )
                            continue

                        # Update designer data
                        self.storage.update_data(
                            designer_data={
                                "season_index": season_index,
                                "data": {
                                    "name": designer["name"],
                                    "url": designer["url"],
                                    "slideshow_url": slideshow_url,
                                },
                                "total_looks": 0,  # Will be updated during image processing
                            }
                        )

                        # Process runway images
                        images_handler = self.scraper._create_images_handler(
                            season_index, designer_index
                        )
                        images_handler.get_runway_images(slideshow_url)

                    except Exception as e:
                        self.logger.error(f"Error processing designer {designer['name']}: {str(e)}")
                        continue

                    # Save progress after each designer
                    self.storage.save_progress()

            else:
                self.logger.info(f"Season already completed: {season['season']} {season['year']}")

        except Exception as e:
            self.logger.error(
                f"Error processing season {season['season']} {season['year']}: {str(e)}"
            )
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
        - Storage initialization
        - Scraper setup
        - Authentication
        - Season processing
        - Progress tracking
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
                    if not any(word in season["season"] for word in ["MORE FROM", "SEE MORE"]):
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
                    if status.get("progress"):
                        self.logger.info(f"Final progress: {status['progress']}")
            except Exception as e:
                self.logger.error(f"Error logging final status: {str(e)}")

        self.logger.info("=== Vogue Scraper Complete ===")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Vogue Runway Scraper")
    parser.add_argument("--checkpoint", type=str, help="Path to checkpoint file to resume from")
    args = parser.parse_args()

    scraper = VogueRunwayScraper(checkpoint_file=args.checkpoint)
    scraper.run()


if __name__ == "__main__":
    main()
