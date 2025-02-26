"""
Batch processing for look-level parallelization.

This module provides functionality for batch processing of looks in parallel,
managing worker threads and collecting results.
"""

import time
import concurrent.futures
from typing import Dict, Any

from .parallel_look_processor_worker import process_single_look


def process_looks_batch(
    look_urls, 
    season_index, 
    designer_index, 
    storage, 
    logger, 
    max_workers=4
):
    """
    Process a batch of looks in parallel.
    
    Args:
        look_urls: Dictionary mapping look numbers to their URLs
        season_index: Index of the season
        designer_index: Index of the designer
        storage: Storage handler
        logger: Logger instance
        max_workers: Maximum number of concurrent workers
        
    Returns:
        Dict containing batch processing results
    """
    batch_start_time = time.time()
    batch_results = {
        "processed_looks": 0,
        "total_looks": len(look_urls),
        "errors": [],
        "runtime_stats": {
            "start_time": batch_start_time,
            "end_time": None,
            "duration": None,
            "looks_per_minute": None
        }
    }
    
    logger.info(f"Processing {len(look_urls)} looks in parallel with {max_workers} workers")
    
    # Process looks in parallel using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_workers, len(look_urls))) as executor:
        # Submit tasks for each look
        future_to_look = {}
        for look_number, look_url in look_urls.items():
            future = executor.submit(
                process_single_look,
                look_url,
                look_number,
                season_index,
                designer_index,
                logger,
                storage
            )
            future_to_look[future] = look_number
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_look):
            look_number = future_to_look[future]
            try:
                result = future.result()
                batch_results["processed_looks"] += 1
                
                if not result.get("success", False):
                    error_msg = f"Failed to process look {look_number}"
                    logger.error(error_msg)
                    batch_results["errors"].append(error_msg)
                
                # Log progress
                if batch_results["processed_looks"] % 5 == 0:
                    logger.info(f"Progress: {batch_results['processed_looks']}/{batch_results['total_looks']} looks")
                
            except Exception as e:
                error_msg = f"Exception processing look {look_number}: {str(e)}"
                logger.error(error_msg)
                batch_results["errors"].append(error_msg)
    
    # Calculate runtime statistics
    batch_end_time = time.time()
    batch_duration = batch_end_time - batch_start_time
    looks_per_minute = (batch_results["processed_looks"] / batch_duration) * 60 if batch_duration > 0 else 0
    
    batch_results["runtime_stats"]["end_time"] = batch_end_time
    batch_results["runtime_stats"]["duration"] = batch_duration
    batch_results["runtime_stats"]["looks_per_minute"] = looks_per_minute
    
    logger.info(f"Batch processing complete: {batch_results['processed_looks']} looks in {batch_duration:.2f}s")
    logger.info(f"Processing rate: {looks_per_minute:.2f} looks per minute")
    
    return batch_results