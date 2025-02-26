"""Workload distribution utilities for parallel processing.

This module provides utilities for distributing and executing work
across multiple workers in parallel.
"""

import logging
import concurrent.futures
from typing import List, Any, Optional, Callable


def distribute_workload(items: List[Any], num_workers: int) -> List[List[Any]]:
    """
    Distribute workload evenly among workers.
    
    Args:
        items: List of items to distribute
        num_workers: Number of workers
        
    Returns:
        List of lists, each containing items for one worker
    """
    if num_workers <= 0:
        return [items]
    
    # Calculate items per worker
    items_per_worker = len(items) // num_workers
    remainder = len(items) % num_workers
    
    # Distribute items
    result = []
    start_idx = 0
    
    for i in range(num_workers):
        # Add one extra item to some workers if there's a remainder
        worker_items = items_per_worker + (1 if i < remainder else 0)
        end_idx = start_idx + worker_items
        
        # Prevent index out of range
        if end_idx > len(items):
            end_idx = len(items)
            
        # Add this worker's items
        if start_idx < end_idx:  # Only add non-empty slices
            result.append(items[start_idx:end_idx])
            
        # Update start index for next worker
        start_idx = end_idx
    
    # Remove any empty batches
    return [batch for batch in result if batch]


def run_in_parallel(func: Callable, items: List[Any], max_workers: int, 
                   logger: Optional[logging.Logger] = None) -> List[Any]:
    """
    Run a function on multiple items in parallel.
    
    Args:
        func: Function to run on each item
        items: List of items to process
        max_workers: Maximum number of workers
        logger: Optional logger for tracking
        
    Returns:
        List of results from the function calls
    """
    results = []
    actual_workers = min(max_workers, len(items))
    
    if logger:
        logger.info(f"Running {len(items)} items in parallel with {actual_workers} workers")
    
    if actual_workers <= 1 or len(items) <= 1:
        # Just run sequentially for single items or single worker
        return [func(item) for item in items]
    
    # Run in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=actual_workers) as executor:
        futures = {executor.submit(func, item): i for i, item in enumerate(items)}
        results = [None] * len(items)  # Pre-allocate result list
        
        for future in concurrent.futures.as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
                if logger:
                    logger.debug(f"Completed item {idx+1}/{len(items)}")
            except Exception as e:
                if logger:
                    logger.error(f"Error processing item {idx+1}: {str(e)}")
                results[idx] = None
    
    return results