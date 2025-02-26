"""
Designer-level parallel processing for Vogue Runway scraper.

This module provides functionality for processing designers in parallel,
handling designer data extraction and slideshow processing.
"""

import threading
import traceback
import time
from typing import Dict, Any, Optional
from selenium.webdriver.remote.webdriver import WebDriver

from src.exceptions.errors import StorageError
from src.handlers.slideshow.main_scrapper import VogueSlideshowScraper
from src.utils.storage.progress_tracker import ProgressTracker


def process_single_designer(
    designer: Dict[str, str], 
    driver: WebDriver,
    storage,
    season_index: int,
    designer_index: int,
    status_lock: threading.Lock,
    worker_status: Dict[int, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Process a single designer with the given driver.
    
    Args:
        designer: Designer data dictionary
        driver: WebDriver instance
        storage: Storage handler
        season_index: Index of the season
        designer_index: Index of the designer
        status_lock: Lock for thread-safe status updates
        worker_status: Dictionary to track worker status
        
    Returns:
        Dict containing designer processing results
    """
    result = {"designer": designer, "completed": False, "errors": []}
    driver_id = id(driver) % 1000  # Use last 3 digits of memory address as driver ID
    
    try:
        # Update thread status
        with status_lock:
            thread_id = threading.get_ident()
            worker_status[thread_id] = {
                "driver_id": driver_id,
                "designer": designer["name"],
                "start_time": time.time(),
                "status": "initializing"
            }
        
        logger = storage.logger
        logger.info(f"[Driver {driver_id}] Processing designer {designer['name']}")
        
        # Update designer data in storage
        designer_data = {
            "season_index": season_index,
            "designer_index": designer_index,
            "data": {
                "name": designer["name"],
                "url": designer["url"],
                "looks": [],
            },
            "total_looks": 0,
            "extracted_looks": 0,
        }
        
        # Update status
        with status_lock:
            worker_status[thread_id]["status"] = "updating_storage"
        
        success = storage.update_data(designer_data=designer_data)
        if not success:
            raise StorageError(f"Failed to update data for designer {designer['name']}")
        
        # Update status
        with status_lock:
            worker_status[thread_id]["status"] = "scraping_slideshow"
        
        # Process the designer's slideshow
        slideshow_scraper = VogueSlideshowScraper(driver, logger, storage)
        
        # Create a progress tracker
        progress_tracker = ProgressTracker(storage, logger)
        
        # Start designer session - this needs to be thread-safe
        # We'll use a unique session ID based on thread ID
        session_id = f"{designer['url']}_{thread_id}"
        storage._start_designer_session(session_id)
        
        # Scrape the designer's slideshow
        with status_lock:
            worker_status[thread_id]["status"] = "scraping_active"
        
        success = slideshow_scraper.scrape_designer_slideshow(
            designer["url"],
            season_index,
            designer_index,
            progress_tracker
        )
        
        # End designer session
        storage._end_designer_session()
        
        # Update progress
        with status_lock:
            worker_status[thread_id]["status"] = "finalizing"
        
        progress_tracker.update_overall_progress()
        storage.save_progress()
        
        if success:
            result["completed"] = True
            logger.info(f"[Driver {driver_id}] Successfully processed designer {designer['name']}")
        else:
            error_msg = f"Failed to process designer {designer['name']}"
            logger.error(f"[Driver {driver_id}] {error_msg}")
            result["errors"].append(error_msg)
        
        # Update status
        with status_lock:
            worker_status[thread_id]["status"] = "completed"
            worker_status[thread_id]["end_time"] = time.time()
            worker_status[thread_id]["success"] = success
        
    except Exception as e:
        error_msg = f"Error processing designer {designer['name']}: {str(e)}"
        logger.error(f"[Driver {driver_id}] {error_msg}")
        traceback.print_exc()
        result["errors"].append(error_msg)
        
        # Update error status
        with status_lock:
            worker_status[thread_id]["status"] = "error"
            worker_status[thread_id]["error"] = str(e)
            worker_status[thread_id]["end_time"] = time.time()
        
        # End designer session if it was started
        if hasattr(storage, "_active_session") and storage._active_session:
            storage._end_designer_session()
    
    return result


def batch_process_designers(designers, season_index, driver_pool, storage, logger, status_lock, worker_status, max_workers):
    """Process a batch of designers in parallel with a pool of drivers.
    
    Args:
        designers: List of designer data dictionaries
        season_index: Index of the season
        driver_pool: List of WebDriver instances
        storage: Storage handler
        logger: Logger instance
        status_lock: Lock for thread-safe status updates
        worker_status: Dictionary to track worker status
        max_workers: Maximum number of parallel workers
        
    Returns:
        Dict containing batch processing results
    """
    import concurrent.futures
    import time
    
    batch_start_time = time.time()
    batch_results = {
        "processed_designers": 0,
        "completed_designers": 0,
        "errors": [],
        "runtime_stats": {
            "start_time": batch_start_time,
            "end_time": None,
            "duration": None,
            "designers_per_minute": None
        }
    }
    
    # Filter out completed designers
    designers_to_process = []
    for i, designer in enumerate(designers):
        if not storage.is_designer_completed(designer["url"]):
            designers_to_process.append((i, designer))
        else:
            batch_results["completed_designers"] += 1
            logger.info(f"Designer {designer['name']} already completed, skipping")
    
    logger.info(f"Processing batch of {len(designers_to_process)} designers with {len(driver_pool)} drivers")
    
    # Define actual max workers based on available drivers and designers
    actual_workers = min(max_workers, len(driver_pool), len(designers_to_process))
    
    if actual_workers == 0:
        logger.info("No designers to process in this batch")
        return batch_results
    
    # Process designers in parallel using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=actual_workers) as executor:
        future_to_designer = {}
        
        # Submit tasks for each designer
        for i, (designer_index, designer) in enumerate(designers_to_process):
            driver_idx = i % len(driver_pool)
            driver = driver_pool[driver_idx]
            
            future = executor.submit(
                process_single_designer,
                designer,
                driver,
                storage,
                season_index,
                designer_index,
                status_lock,
                worker_status
            )
            future_to_designer[future] = designer
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_designer):
            designer = future_to_designer[future]
            try:
                result = future.result()
                batch_results["processed_designers"] += 1
                
                if result.get("completed", False):
                    batch_results["completed_designers"] += 1
                
                if result.get("errors"):
                    batch_results["errors"].extend(result["errors"])
                
                logger.info(f"Finished processing designer {designer['name']}")
            except Exception as e:
                error_msg = f"Exception processing designer {designer['name']}: {str(e)}"
                logger.error(error_msg)
                batch_results["errors"].append(error_msg)
    
    # Calculate runtime statistics
    batch_end_time = time.time()
    batch_duration = batch_end_time - batch_start_time
    designers_per_minute = (batch_results["processed_designers"] / batch_duration) * 60 if batch_duration > 0 else 0
    
    batch_results["runtime_stats"]["end_time"] = batch_end_time
    batch_results["runtime_stats"]["duration"] = batch_duration
    batch_results["runtime_stats"]["designers_per_minute"] = designers_per_minute
    
    logger.info(f"Batch processing complete: {batch_results['processed_designers']} designers in {batch_duration:.2f}s")
    logger.info(f"Processing rate: {designers_per_minute:.2f} designers per minute")
    
    return batch_results