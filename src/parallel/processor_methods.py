
"""
Core processor methods for parallel scraping.

This module implements the main parallel processing methods for
season and designer parallel processing.
"""

import concurrent.futures
import time
import logging
from typing import Dict, List, Any

from src.exceptions.errors import ScraperError
from src.handlers.designers import VogueDesignersHandler
from src.parallel.parallel_season_processor import process_single_season
from src.parallel.parallel_designer_processor import process_single_designer

# Note: If this file needs ParallelProcessingManager, import it like this:
# from src.parallel_processor import ParallelProcessingManager

def process_multiple_seasons_parallel(
    manager, 
    seasons: List[Dict[str, str]], 
    driver_pool: List,
    storage,
    max_workers: int,
    logger
) -> Dict[str, Any]:
    """
    Process multiple seasons in parallel.
    
    Args:
        manager: ParallelProcessingManager instance
        seasons: List of season data dictionaries
        driver_pool: List of WebDriver instances
        storage: Storage handler instance
        max_workers: Maximum number of parallel workers
        logger: Logger instance
        
    Returns:
        Dict containing processing results and statistics
    """
    logger.info(f"Processing {len(seasons)} seasons with {max_workers} parallel workers")
    start_time = time.time()
    results = {"processed_seasons": 0, "completed_designers": 0, "errors": []}
    
    # Filter out seasons that are already completed
    seasons_to_process = []
    for season in seasons:
        if not storage.is_season_completed(season):
            seasons_to_process.append(season)
        else:
            logger.info(f"Season {season['season']} {season['year']} already completed, skipping")
    
    logger.info(f"{len(seasons_to_process)}/{len(seasons)} seasons need processing")
    
    # Process seasons in parallel using a ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_workers, len(seasons_to_process))) as executor:
        # Create a map of season to driver
        season_tasks = {}
        for i, season in enumerate(seasons_to_process):
            # Get driver index using modulo to handle case where seasons > drivers
            driver_idx = i % len(driver_pool)
            driver = driver_pool[driver_idx]
            
            # Submit the season processing task
            season_tasks[executor.submit(
                process_single_season, 
                season, 
                driver,
                storage,
                logger
            )] = season
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(season_tasks):
            season = season_tasks[future]
            try:
                season_result = future.result()
                results["processed_seasons"] += 1
                results["completed_designers"] += season_result.get("completed_designers", 0)
                logger.info(f"Completed season {season['season']} {season['year']} with {season_result.get('completed_designers', 0)} designers")
            except Exception as e:
                error_msg = f"Error processing season {season['season']} {season['year']}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
    
    # Calculate statistics
    end_time = time.time()
    results["total_time"] = end_time - start_time
    results["avg_time_per_season"] = results["total_time"] / max(results["processed_seasons"], 1)
    
    logger.info(f"Parallel season processing complete in {results['total_time']:.2f} seconds")
    logger.info(f"Processed {results['processed_seasons']} seasons with {len(results['errors'])} errors")
    
    return results


def process_designers_parallel(
    manager,
    season: Dict[str, str],
    driver_pool: List,
    storage,
    max_workers: int,
    worker_status: Dict,
    status_lock,
    logger
) -> Dict[str, Any]:
    """
    Process designers within a season in parallel.
    
    Args:
        manager: ParallelProcessingManager instance
        season: Season data dictionary
        driver_pool: List of WebDriver instances
        storage: Storage handler instance
        max_workers: Maximum number of parallel workers
        worker_status: Dictionary to track worker status
        status_lock: Lock for thread-safe status updates
        logger: Logger instance
        
    Returns:
        Dict containing processing results and statistics
    """
    logger.info(f"Processing designers for season {season['season']} {season['year']} in parallel")
    start_time = time.time()
    results = {"season": season, "processed_designers": 0, "completed_designers": 0, "errors": []}
    
    # Check if season is already completed
    if storage.is_season_completed(season):
        logger.info(f"Season {season['season']} {season['year']} already completed, skipping")
        return results
    
    # Get season index
    storage.update_data(season_data=season)
    current_data = storage.read_data()
    season_index = None
    for i, s in enumerate(current_data["seasons"]):
        if s["season"] == season["season"] and s["year"] == season["year"]:
            season_index = i
            break
    
    if season_index is None:
        raise ScraperError(f"Season {season['season']} {season['year']} not found in storage")
    
    # Get designers for this season using the first driver
    if not driver_pool:
        raise ScraperError("No WebDriver instances available for parallel processing")
    
    primary_driver = driver_pool[0]
    designers_handler = VogueDesignersHandler(primary_driver, logger)
    designers = designers_handler.get_designers_for_season(season["url"])
    
    if not designers:
        logger.warning(f"No designers found for season {season['season']} {season['year']}")
        return results
    
    # Filter out designers that are already completed
    designers_to_process = []
    for designer in designers:
        if not storage.is_designer_completed(designer["url"]):
            designers_to_process.append(designer)
        else:
            results["completed_designers"] += 1
            logger.info(f"Designer {designer['name']} already completed, skipping")
    
    logger.info(f"Need to process {len(designers_to_process)}/{len(designers)} designers")
    
    # Process designers in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_workers, len(designers_to_process))) as executor:
        # Create a map of designer to driver and track futures
        designer_tasks = {}
        for i, designer in enumerate(designers_to_process):
            # Get driver index using modulo to handle case where designers > drivers
            driver_idx = i % len(driver_pool)
            driver = driver_pool[driver_idx]
            
            # Track which driver is processing which designer
            logger.info(f"Assigning driver {driver_idx} to designer {designer['name']}")
            
            # Submit the designer processing task
            designer_tasks[executor.submit(
                process_single_designer, 
                designer, 
                driver,
                storage,
                season_index,
                i,  # designer_index
                status_lock,
                worker_status
            )] = designer
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(designer_tasks):
            designer = designer_tasks[future]
            try:
                designer_result = future.result()
                results["processed_designers"] += 1
                if designer_result.get("completed", False):
                    results["completed_designers"] += 1
                logger.info(f"Completed designer {designer['name']} with result: {designer_result}")
            except Exception as e:
                error_msg = f"Error processing designer {designer['name']}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
    
    # Calculate statistics
    end_time = time.time()
    results["total_time"] = end_time - start_time
    results["avg_time_per_designer"] = results["total_time"] / max(results["processed_designers"], 1)
    
    logger.info(f"Parallel designer processing complete in {results['total_time']:.2f} seconds")
    logger.info(f"Processed {results['processed_designers']} designers with {len(results['errors'])} errors")
    
    return results