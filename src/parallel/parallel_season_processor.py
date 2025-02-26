"""
Season-level parallel processing for Vogue Runway scraper.

This module provides functionality for processing seasons in parallel,
handling designer extraction and processing for entire seasons.
"""

import traceback
from typing import Dict, Any, Optional
from selenium.webdriver.remote.webdriver import WebDriver

from src.exceptions.errors import ScraperError


def process_single_season(
    season: Dict[str, str], 
    driver: WebDriver, 
    storage, 
    logger
) -> Dict[str, Any]:
    """
    Process a single season with the given driver.
    
    Args:
        season: Season data dictionary
        driver: WebDriver instance
        storage: Storage handler
        logger: Logger instance
        
    Returns:
        Dict containing season processing results
    """
    result = {"season": season, "completed_designers": 0, "errors": []}
    
    try:
        # First update the season data in storage
        storage.update_data(season_data=season)
        
        # Get season index
        current_data = storage.read_data()
        season_index = None
        for i, s in enumerate(current_data["seasons"]):
            if s["season"] == season["season"] and s["year"] == season["year"]:
                season_index = i
                break
        
        if season_index is None:
            raise ScraperError(f"Season {season['season']} {season['year']} not found in storage")
        
        # Get designers for this season
        from src.handlers.designers import VogueDesignersHandler
        designers_handler = VogueDesignersHandler(driver, logger)
        designers = designers_handler.get_designers_for_season(season["url"])
        
        if not designers:
            logger.warning(f"No designers found for season {season['season']} {season['year']}")
            return result
        
        logger.info(f"Found {len(designers)} designers for season {season['season']} {season['year']}")
        
        # Process each designer sequentially within this season
        for designer_index, designer in enumerate(designers):
            try:
                # Check if designer is already completed
                if storage.is_designer_completed(designer["url"]):
                    logger.info(f"Designer {designer['name']} already completed, skipping")
                    result["completed_designers"] += 1
                    continue
                
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
                
                storage.update_data(designer_data=designer_data)
                
                # Process the designer's slideshow
                slideshow_scraper = create_slideshow_scraper(driver, logger, storage)
                
                # Create a progress tracker
                progress_tracker = create_progress_tracker(storage, logger)
                
                # Start designer session
                storage._start_designer_session(designer["url"])
                
                # Scrape the designer's slideshow
                success = slideshow_scraper.scrape_designer_slideshow(
                    designer["url"],
                    season_index,
                    designer_index,
                    progress_tracker
                )
                
                # End designer session
                storage._end_designer_session()
                
                if success:
                    result["completed_designers"] += 1
                    logger.info(f"Successfully processed designer {designer['name']}")
                else:
                    error_msg = f"Failed to process designer {designer['name']}"
                    logger.error(error_msg)
                    result["errors"].append(error_msg)
                
                # Update progress
                progress_tracker.update_overall_progress()
                storage.save_progress()
                
            except Exception as designer_error:
                error_msg = f"Error processing designer {designer['name']}: {str(designer_error)}"
                logger.error(error_msg)
                traceback.print_exc()
                result["errors"].append(error_msg)
                
                # End designer session if it was started
                if hasattr(storage, "_active_session") and storage._active_session:
                    storage._end_designer_session()
        
        # Mark season as processed
        logger.info(f"Completed season {season['season']} {season['year']} with {result['completed_designers']}/{len(designers)} designers")
        
    except Exception as e:
        error_msg = f"Error in season processing: {str(e)}"
        logger.error(error_msg)
        traceback.print_exc()
        result["errors"].append(error_msg)
    
    return result


def create_slideshow_scraper(driver, logger, storage):
    """Create a slideshow scraper instance."""
    from src.handlers.slideshow.main_scrapper import VogueSlideshowScraper
    return VogueSlideshowScraper(driver, logger, storage)


def create_progress_tracker(storage, logger):
    """Create a progress tracker instance."""
    from src.utils.storage.progress_tracker import ProgressTracker
    return ProgressTracker(storage, logger)


def process_season_batch(seasons, drivers, storage, logger, max_workers):
    """
    Process a batch of seasons with a pool of drivers.
    
    Args:
        seasons: List of season data dictionaries
        drivers: List of WebDriver instances
        storage: Storage handler
        logger: Logger instance
        max_workers: Maximum number of parallel workers
        
    Returns:
        Dict containing batch processing results
    """
    import concurrent.futures
    import time
    
    batch_start_time = time.time()
    batch_results = {
        "processed_seasons": 0, 
        "completed_designers": 0, 
        "errors": [],
        "runtime_stats": {
            "start_time": batch_start_time,
            "end_time": None,
            "duration": None,
            "seasons_per_minute": None
        }
    }
    
    # Filter completed seasons
    seasons_to_process = [s for s in seasons if not storage.is_season_completed(s)]
    logger.info(f"Processing batch of {len(seasons_to_process)} seasons with {len(drivers)} drivers")
    
    # Define actual max workers based on available drivers and seasons
    actual_workers = min(max_workers, len(drivers), len(seasons_to_process))
    
    if actual_workers == 0:
        logger.info("No seasons to process in this batch")
        return batch_results
    
    # Process seasons in parallel using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=actual_workers) as executor:
        # Map seasons to drivers using round-robin assignment
        future_to_season = {}
        for i, season in enumerate(seasons_to_process):
            driver_idx = i % len(drivers)
            driver = drivers[driver_idx]
            
            future = executor.submit(
                process_single_season,
                season,
                driver,
                storage,
                logger
            )
            future_to_season[future] = season
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_season):
            season = future_to_season[future]
            try:
                result = future.result()
                batch_results["processed_seasons"] += 1
                batch_results["completed_designers"] += result.get("completed_designers", 0)
                
                if result.get("errors"):
                    batch_results["errors"].extend(result["errors"])
                    
                logger.info(f"Finished processing season {season['season']} {season['year']}")
            except Exception as e:
                error_msg = f"Exception processing season {season['season']} {season['year']}: {str(e)}"
                logger.error(error_msg)
                batch_results["errors"].append(error_msg)
    
    # Calculate runtime statistics
    batch_end_time = time.time()
    batch_duration = batch_end_time - batch_start_time
    seasons_per_minute = (batch_results["processed_seasons"] / batch_duration) * 60 if batch_duration > 0 else 0
    
    batch_results["runtime_stats"]["end_time"] = batch_end_time
    batch_results["runtime_stats"]["duration"] = batch_duration
    batch_results["runtime_stats"]["seasons_per_minute"] = seasons_per_minute
    
    logger.info(f"Batch processing complete: {batch_results['processed_seasons']} seasons in {batch_duration:.2f}s")
    logger.info(f"Processing rate: {seasons_per_minute:.2f} seasons per minute")
    
    return batch_results