"""
Look-level parallel processing methods.

This module implements the methods for processing looks in parallel, which follows
a different approach from season and designer parallel processing.
"""

from typing import Dict, Any, List
import logging
import time

from src.utils.driver import setup_chrome_driver
from src.utils.storage.progress_tracker import ProgressTracker
from src.parallel.parallel_look_processor import ParallelLookScraper


def process_looks_parallel(
    manager,
    designer_url: str, 
    season_index: int, 
    designer_index: int,
    driver_pool: List,
    storage,
    max_workers: int,
    logger: logging.Logger
) -> Dict[str, Any]:
    """
    Process looks for a designer in parallel.
    
    This method uses a different approach - it uses a single WebDriver to navigate to
    the slideshow, then dispatches multiple workers to process different looks.
    
    Args:
        manager: ParallelProcessingManager instance
        designer_url: URL of the designer's page
        season_index: Index of the season
        designer_index: Index of the designer
        driver_pool: List of WebDriver instances
        storage: Storage handler instance
        max_workers: Maximum number of parallel workers
        logger: Logger instance
        
    Returns:
        Dict containing processing results and statistics
    """
    logger.info(f"Processing looks for designer in parallel: {designer_url}")
    result = {"processed_looks": 0, "errors": []}
    
    try:
        # We only need one driver for this mode
        if not driver_pool:
            driver = setup_chrome_driver()
            driver_pool.append(driver)
        
        driver = driver_pool[0]
        
        # Start designer session
        storage._start_designer_session(designer_url)
        
        # Initialize the slideshow scraper
        look_scraper = ParallelLookScraper(
            driver, 
            logger, 
            storage,
            max_workers=max_workers
        )
        
        # Create a progress tracker
        progress_tracker = ProgressTracker(storage, logger)
        
        # Scrape the looks in parallel
        success, stats = look_scraper.scrape_designer_slideshow_parallel(
            designer_url,
            season_index,
            designer_index,
            progress_tracker
        )
        
        # Update result with stats
        result.update(stats)
        
        # End designer session
        storage._end_designer_session()
        
        # Update progress
        progress_tracker.update_overall_progress()
        storage.save_progress()
        
        logger.info(f"Parallel look processing complete for {designer_url}")
        logger.info(f"Processed {result['processed_looks']} looks with {len(result['errors'])} errors")
        
    except Exception as e:
        error_msg = f"Error in parallel look processing: {str(e)}"
        logger.error(error_msg)
        result["errors"].append(error_msg)
        
        # End designer session if it was started
        if hasattr(storage, "_active_session") and storage._active_session:
            storage._end_designer_session()
    
    return result