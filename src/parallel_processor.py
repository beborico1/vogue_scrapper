"""
Main parallel processing manager for Vogue Runway scraper.

This module provides the core class for parallel processing capabilities,
managing resources and coordinating different parallel processing strategies.
"""

import concurrent.futures
import threading
import queue
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

from selenium.webdriver.remote.webdriver import WebDriver

from src.utils.driver import setup_chrome_driver
from src.utils.logging import setup_logger
from src.utils.storage.storage_factory import StorageFactory
from src.exceptions.errors import ScraperError, StorageError
from src.config.settings import BASE_URL, AUTH_URL

# Import specialized processors
from src.parallel.parallel_season_processor import process_single_season
from src.parallel.parallel_designer_processor import process_single_designer
from src.parallel.parallel_look_processor import ParallelLookScraper
from src.parallel.parallel_utils import share_authentication

# Import specific processors from new module files
from src.parallel.processor_methods import process_designers_parallel, process_multiple_seasons_parallel


class ParallelProcessingManager:
    """
    Manages parallel processing for the Vogue Runway scraper.
    
    This class provides different parallelization strategies:
    1. Multi-designer: Process multiple designers in parallel while seasons are processed sequentially
    2. Multi-season: Process multiple seasons in parallel (highest level of parallelism)
    3. Multi-look: Process multiple looks within a designer's collection in parallel
    
    Each strategy comes with different trade-offs in terms of resource usage and complexity.
    """
    
    def __init__(self, 
                 max_workers: int = 4, 
                 mode: str = "multi-designer",
                 checkpoint_file: Optional[str] = None,
                 storage_mode: Optional[str] = None):
        """
        Initialize the parallel processing manager.
        
        Args:
            max_workers: Maximum number of parallel workers
            mode: Parallelization mode ('multi-designer', 'multi-season', or 'multi-look')
            checkpoint_file: Optional path to checkpoint file to resume from
            storage_mode: Optional storage mode override ('json' or 'redis')
        """
        self.logger = setup_logger()
        self.max_workers = max_workers
        self.mode = mode
        self.checkpoint_file = checkpoint_file
        self.storage_mode = storage_mode
        
        # Thread-safe collections
        self.result_queue = queue.Queue()
        self.error_queue = queue.Queue()
        self.worker_status = {}
        self.status_lock = threading.Lock()
        
        # Driver pool and storage handlers will be initialized when needed
        self.driver_pool = []
        self.storage = None
        
        self.logger.info(f"Initialized parallel processing manager with {max_workers} workers in {mode} mode")
    
    def initialize_resources(self) -> None:
        """Initialize driver pool and storage handler."""
        self.logger.info("Initializing resources for parallel processing")
        
        # Initialize storage
        self.storage = StorageFactory.create_storage_handler(self.checkpoint_file)
        
        # Initialize driver pool based on mode
        if self.mode == "multi-designer" or self.mode == "multi-season":
            self._initialize_driver_pool()
        
        self.logger.info("Resource initialization complete")
    
    def _initialize_driver_pool(self) -> None:
        """Initialize a pool of WebDriver instances with authentication."""
        self.logger.info(f"Creating WebDriver pool with {self.max_workers} drivers")
        
        # Create and authenticate the first driver
        try:
            primary_driver = setup_chrome_driver()
            # Authenticate the primary driver
            from src.handlers.auth import VogueAuthHandler
            auth_handler = VogueAuthHandler(primary_driver, self.logger, BASE_URL)
            if not auth_handler.authenticate(AUTH_URL):
                raise ScraperError("Failed to authenticate primary driver")
            
            self.driver_pool.append(primary_driver)
            self.logger.info("Primary driver authenticated successfully")
            
            # Create additional drivers and share authentication
            for i in range(1, self.max_workers):
                try:
                    driver = setup_chrome_driver()
                    
                    # Share authentication from primary driver
                    share_authentication(primary_driver, driver, self.logger, BASE_URL)
                    
                    self.driver_pool.append(driver)
                    self.logger.info(f"Initialized and authenticated driver {i+1}/{self.max_workers}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to initialize driver {i+1}: {str(e)}")
                    # Continue even if some drivers fail to initialize
        except Exception as e:
            self.logger.error(f"Failed to initialize primary driver: {str(e)}")
            raise
        
        if not self.driver_pool:
            raise ScraperError("Failed to initialize any WebDriver instances")
    
    def cleanup_resources(self) -> None:
        """Clean up all resources including driver pool."""
        self.logger.info("Cleaning up resources")
        
        # Quit all WebDriver instances
        for driver in self.driver_pool:
            try:
                driver.quit()
                self.logger.info("Driver instance closed successfully")
            except Exception as e:
                self.logger.error(f"Error closing driver: {str(e)}")
        
        # Clear the pool
        self.driver_pool.clear()
        
        # Save final progress
        if self.storage and hasattr(self.storage, "save_progress"):
            try:
                self.storage.save_progress()
                self.logger.info("Final progress saved successfully")
            except Exception as e:
                self.logger.error(f"Error saving final progress: {str(e)}")
        
        self.logger.info("Resource cleanup complete")
    
    def process_seasons_parallel(self, seasons: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Process multiple seasons in parallel.
        
        Args:
            seasons: List of season data dictionaries
            
        Returns:
            Dict containing processing results and statistics
        """
        return process_multiple_seasons_parallel(
            self, seasons, self.driver_pool, self.storage, self.max_workers, self.logger
        )
    
    def process_designers_parallel(self, season: Dict[str, str]) -> Dict[str, Any]:
        """
        Process designers within a season in parallel.
        
        Args:
            season: Season data dictionary
            
        Returns:
            Dict containing processing results and statistics
        """
        return process_designers_parallel(
            self, season, self.driver_pool, self.storage, self.max_workers, 
            self.worker_status, self.status_lock, self.logger
        )
    
    def process_looks_parallel(self, 
                              designer_url: str, 
                              season_index: int, 
                              designer_index: int) -> Dict[str, Any]:
        """
        Process looks for a designer in parallel.
        
        This method uses a different approach - it uses a single WebDriver to navigate to
        the slideshow, then dispatches multiple workers to process different looks.
        
        Args:
            designer_url: URL of the designer's page
            season_index: Index of the season
            designer_index: Index of the designer
            
        Returns:
            Dict containing processing results and statistics
        """
        from src.parallel.processor_looks import process_looks_parallel
        return process_looks_parallel(
            self, designer_url, season_index, designer_index,
            self.driver_pool, self.storage, self.max_workers, self.logger
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of all workers."""
        with self.status_lock:
            return {
                "mode": self.mode,
                "max_workers": self.max_workers,
                "active_workers": len(self.worker_status),
                "workers": self.worker_status
            }