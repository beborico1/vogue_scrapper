"""Scraper orchestrator for Vogue Runway - Part 2.

This module contains additional methods for the VogueRunwayScraper class
that handle parallel season processing and resuming from checkpoints.
"""

from typing import Dict, Optional, List, Tuple, Any
from datetime import datetime
import time

from src.exceptions.errors import AuthenticationError, ScraperError, StorageError
from src.parallel_processor import ParallelProcessingManager  # Import directly from parallel_processor
from src.config.settings import AUTH_URL

class VogueRunwayScraperPart2:
    """Continuation of VogueRunwayScraper class methods."""

    def process_multiple_seasons_parallel(self, seasons: List[Dict[str, str]]) -> None:
        """Process multiple seasons in parallel.
        
        Args:
            seasons: List of season data dictionaries to process
        """
        if not self.parallel or self.parallel_mode != "multi-season":
            self.logger.error("This method requires parallel mode to be 'multi-season'")
            return
            
        try:
            self.logger.info(f"Processing {len(seasons)} seasons in parallel")
            
            # Initialize parallel manager if needed
            if not self.parallel_manager:
                self.parallel_manager = ParallelProcessingManager(
                    max_workers=self.max_workers,
                    mode="multi-season",
                    checkpoint_file=self.current_file
                )
                self.parallel_manager.initialize_resources()
            
            # Process seasons in parallel
            result = self.parallel_manager.process_seasons_parallel(seasons)
            
            self.logger.info(f"Parallel processing results: {result['processed_seasons']} of {len(seasons)} seasons completed")
            if result["errors"]:
                self.logger.warning(f"Encountered {len(result['errors'])} errors during parallel processing")
                for error in result["errors"]:
                    self.logger.warning(f"Error: {error}")
            
        except Exception as e:
            self.logger.error(f"Error in parallel season processing: {str(e)}")
            raise ScraperError(f"Parallel season processing failed: {str(e)}")

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
        """Execute the main scraping process with parallel processing support.

        This method coordinates the entire scraping process, including:
        - Storage initialization and validation
        - Scraper setup and authentication
        - Automatic checkpoint management
        - Parallel or sequential season processing
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

            # Process seasons based on mode
            current_data = self.storage.read_data()
            seasons_to_process = current_data["seasons"][start_index:]
            
            if self.parallel and self.parallel_mode == "multi-season":
                # Process all remaining seasons in parallel
                self.process_multiple_seasons_parallel(seasons_to_process)
            else:
                # Process seasons sequentially
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
            # Clean up parallel resources if used
            if self.parallel and self.parallel_manager:
                self.parallel_manager.cleanup_resources()
            
            # Clean up driver
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