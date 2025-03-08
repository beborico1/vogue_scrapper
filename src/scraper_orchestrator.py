"""Scraper orchestrator for Vogue Runway with improved waiting mechanisms.

This module contains the main scraper orchestrator that supports both sequential
and parallel processing modes with robust error handling and checkpointing.
"""

import os
import sys
import threading
from typing import Dict, Optional, List, Tuple, Any
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import queue

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from src.utils.driver import setup_chrome_driver
from src.utils.logging import setup_logger
from src.utils.storage.storage_factory import StorageFactory
from src.config.settings import config, BASE_URL
from src.exceptions.errors import ScraperError, StorageError
from src.handlers.auth import VogueAuthHandler
from src.handlers.slideshow.main_scrapper import VogueSlideshowScraper
from src.utils.storage.progress_tracker import ProgressTracker
from src.parallel_processor import ParallelProcessingManager
from src.handlers.images.operation_handler import retry_operation, with_retry
from src.checkpoint_manager import find_latest_checkpoint


class VogueRunwayScraper:
    """Main scraper orchestrator class with real-time data storage and parallel processing."""

    def __init__(self, checkpoint_file: Optional[str] = None, parallel: bool = False, 
                parallel_mode: str = "multi-designer", max_workers: int = 4):
        """Initialize the scraper orchestrator."""
        self.logger = setup_logger()
        self.parallel = parallel
        self.parallel_mode = parallel_mode
        self.max_workers = max_workers

        # If no checkpoint file is provided, try to find the latest one
        if checkpoint_file is None:
            latest_checkpoint = find_latest_checkpoint()
            if latest_checkpoint:
                self.logger.info(f"Using latest checkpoint: {latest_checkpoint}")
                checkpoint_file = latest_checkpoint
            else:
                self.logger.info("No existing checkpoint found, starting fresh")

        # Handle special Redis checkpoint identifier
        if checkpoint_file and checkpoint_file.startswith("redis:"):
            # For Redis, use the special identifier or extract the specific ID if needed
            redis_checkpoint_id = checkpoint_file.split(":", 1)[1] if ":" in checkpoint_file else None
            self.logger.info(f"Using Redis checkpoint: {redis_checkpoint_id or 'latest'}")
            checkpoint_file = redis_checkpoint_id  # Pass just the ID part to the storage handler
        
        # Create storage handler using factory based on configuration
        self.storage = StorageFactory.create_storage_handler(checkpoint_file)
        self.logger.info(f"Using {config.storage.STORAGE_MODE} storage")
        
        # Initialize parallel processing manager if needed
        if self.parallel:
            self.parallel_manager = ParallelProcessingManager(
                max_workers=max_workers,
                mode=parallel_mode,
                checkpoint_file=checkpoint_file,
                storage_mode=config.storage.STORAGE_MODE
            )
            self.logger.info(f"Parallel processing enabled with {max_workers} workers in {parallel_mode} mode")
        else:
            self.parallel_manager = None
            self.logger.info("Using sequential processing")
        
        self.driver = None
        self.scraper = None
        self.current_file = None
        
        # Thread coordination
        self.processing_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.error_queue = queue.Queue()
        self.completion_event = threading.Event()

    def set_sorting_type(self, sort_type: str) -> None:
        """Set the season sorting type.
        
        Args:
            sort_type: 'asc' for ascending (oldest first) or 'desc' for descending (newest first)
        
        Raises:
            ValueError: If sort_type is not 'asc' or 'desc'
        """
        if sort_type.lower() not in ['asc', 'desc']:
            raise ValueError("Sorting type must be 'asc' or 'desc'")
            
        # Update the global config setting
        from src.config.settings import config
        config.sorting_type = sort_type.lower()
        
        self.logger.info(f"Season sorting set to: {sort_type.lower()} - {'newest first' if sort_type.lower() == 'desc' else 'oldest first'}")

    @with_retry(max_retries=3, retry_delay=2)
    def initialize_scraper(self) -> None:
        """Initialize the Selenium driver and VogueScraper with retry capability.

        Raises:
            ScraperError: If initialization fails
        """
        try:
            self.driver = setup_chrome_driver()
            
            from src.scraper import VogueScraper
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

    def process_season(self, season: Dict[str, str]) -> None:
        """Process a single season's data with parallel processing support.
        
        Args:
            season: Season data dictionary to process
        """
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
                if self.parallel and self.parallel_mode == "multi-designer":
                    # Process designers in parallel
                    self.logger.info(f"Processing designers in parallel for season: {season['url']}")
                    if not self.parallel_manager:
                        self.parallel_manager = ParallelProcessingManager(
                            max_workers=self.max_workers,
                            mode="multi-designer",
                            checkpoint_file=self.current_file
                        )
                    
                    # Ensure resources are properly initialized
                    self.parallel_manager.initialize_resources()
                    
                    # Explicitly set the storage handler to ensure it's available
                    self.parallel_manager.storage = self.storage
                    
                    result = self.parallel_manager.process_designers_parallel(season)
                    self.logger.info(f"Parallel processing result: {result['completed_designers']} of {result['processed_designers']} designers completed")
                    
                else:
                    # Sequential processing of designers
                    self.logger.info(f"Fetching designers for season: {season['url']}")
                    
                    # Use retry for getting designers
                    designers = retry_operation(
                        self.logger,
                        lambda: self.scraper.get_designers_for_season(season["url"]),
                        f"fetch designers for season {season['season']} {season['year']}"
                    )
                    
                    if not designers:
                        self.logger.warning(f"No designers found for season: {season['url']}")
                        return
                        
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

                            # Process in parallel or sequential mode
                            if self.parallel and self.parallel_mode == "multi-look":
                                # Process looks in parallel
                                if not self.parallel_manager:
                                    self.parallel_manager = ParallelProcessingManager(
                                        max_workers=self.max_workers,
                                        mode="multi-look",
                                        checkpoint_file=self.current_file
                                    )
                                    self.parallel_manager.initialize_resources()
                                    # Explicitly set the storage handler
                                    self.parallel_manager.storage = self.storage
                                
                                result = self.parallel_manager.process_looks_parallel(
                                    designer["url"],
                                    season_index,
                                    designer_index
                                )
                                success = result["processed_looks"] > 0
                                self.logger.info(f"Processed {result['processed_looks']} looks in parallel")
                            else:
                                # Use retry for scraping the designer's slideshow
                                success = retry_operation(
                                    self.logger,
                                    lambda: slideshow_scraper.scrape_designer_slideshow(
                                        designer["url"],
                                        season_index,
                                        designer_index,
                                        progress_tracker
                                    ),
                                    f"scrape slideshow for {designer['name']}"
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
            
            # Authenticate using retry
            auth_success = retry_operation(
                self.logger,
                lambda: self.scraper.authenticate(config.AUTH_URL),
                "authentication"
            )
            
            if not auth_success:
                raise ScraperError("Failed to authenticate with Vogue")

            # Check for existing progress
            checkpoint = self.resume_from_checkpoint()
            if checkpoint[0] is not None:
                start_index = checkpoint[0]
                self.logger.info("Resuming from previous checkpoint")
            else:
                start_index = 0
                # Get all seasons if starting fresh
                seasons = retry_operation(
                    self.logger,
                    self.scraper.get_seasons_list,
                    "fetching seasons list"
                )
                
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
                if not self.parallel_manager:
                    self.parallel_manager = ParallelProcessingManager(
                        max_workers=self.max_workers,
                        mode="multi-season",
                        checkpoint_file=self.current_file
                    )
                
                # Ensure resources are properly initialized
                self.parallel_manager.initialize_resources()
                
                # Explicitly set the storage handler
                self.parallel_manager.storage = self.storage
                
                result = self.parallel_manager.process_seasons_parallel(seasons_to_process)
                self.logger.info(f"Parallel processing result: {result['processed_seasons']} seasons processed")
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