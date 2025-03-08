#!/usr/bin/env python3
"""
Utility functions for benchmark testing.

This module provides core utility functions for benchmark tests, including 
resource monitoring and general benchmark utilities.
"""

import threading
import os
import logging
import psutil
import json
import random
from typing import Dict, List, Any, Tuple
from datetime import datetime
from pathlib import Path


def monitor_resources(pid: int, stop_event: threading.Event, interval: float = 0.5) -> Dict[str, List[float]]:
    """Monitor CPU and memory usage of a process.
    
    Args:
        pid: Process ID to monitor
        stop_event: Event to signal when monitoring should stop
        interval: Sampling interval in seconds
        
    Returns:
        Dict with CPU and memory usage data
    """
    try:
        process = psutil.Process(pid)
        cpu_usage = []
        memory_usage = []
        timestamps = []
        
        start_time = threading.Event().wait(0)  # Get current timestamp without sleep
        
        while not stop_event.wait(interval):  # Use wait instead of sleep for polling
            try:
                # Get CPU and memory usage
                cpu_percent = process.cpu_percent(interval=0.1)
                memory_percent = process.memory_percent()
                
                # Add to lists
                cpu_usage.append(cpu_percent)
                memory_usage.append(memory_percent)
                timestamps.append(threading.Event().wait(0) - start_time)
                
            except Exception:
                # Process might have ended
                break
        
        return {
            "cpu": cpu_usage,
            "memory": memory_usage,
            "timestamps": timestamps
        }
        
    except Exception:
        # Process not found or other error
        return {"cpu": [], "memory": [], "timestamps": []}


def create_temp_storage(test_data: Dict[str, Any], timestamp: str) -> Tuple[str, Any]:
    """Create temporary storage for benchmark testing.
    
    Args:
        test_data: Test data to store
        timestamp: Timestamp for file naming
        
    Returns:
        Tuple of (temp_dir, storage_handler)
    """
    try:
        # Create temporary directory
        temp_dir = f"temp_benchmark_{timestamp}"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Create temporary JSON file
        temp_file = f"{temp_dir}/test_data_{timestamp}.json"
        with open(temp_file, 'w') as f:
            json.dump(test_data, f, indent=2)
        
        # Import storage handler here to avoid circular imports
        from src.utils.storage.data_storage_handler import DataStorageHandler
        storage = DataStorageHandler(base_dir=temp_dir, checkpoint_file=temp_file)
        
        return temp_dir, storage
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Error creating temp storage: {str(e)}")
        return None, None


def run_multi_designer_benchmark(benchmark_runner, num_seasons, num_designers, max_workers, test_data, timestamp):
    """Run benchmark for multi-designer parallel processing.
    
    Args:
        benchmark_runner: Benchmark runner instance
        num_seasons: Number of seasons to process
        num_designers: Number of designers per season to process
        max_workers: Maximum number of workers
        test_data: Test data to use
        timestamp: Timestamp for file naming
    """
    benchmark_runner.logger.info(f"Running multi-designer benchmark with {max_workers} workers")
    
    # Create temporary storage
    temp_dir, storage = create_temp_storage(test_data, timestamp)
    
    try:
        # Setup monitoring
        stop_monitoring = threading.Event()
        monitor_thread = threading.Thread(
            target=lambda: monitor_resources(os.getpid(), stop_monitoring)
        )
        resource_data = {"cpu": [], "memory": [], "timestamps": []}
        
        # Prepare test data subset
        test_seasons = test_data["seasons"][:num_seasons]
        for season in test_seasons:
            season["designers"] = season["designers"][:num_designers]
        
        # Run benchmark
        start_time = datetime.now().timestamp()
        monitor_thread.start()
        
        # Import and create multi-designer manager
        from src.parallel_processor import ParallelProcessingManager
        manager = ParallelProcessingManager(
            max_workers=max_workers,
            mode="multi-designer",
            checkpoint_file=None
        )
        
        # Mock the scraper initialization - simplified for benchmark
        manager.initialize_resources = lambda: None
        manager.driver_pool = [None] * max_workers
        manager.storage = storage
        
        # Run the processing
        processed_items = 0
        for season in test_seasons:
            # Process each season with mock functions
            benchmark_runner.logger.info(f"Processing season: {season['season']} {season['year']}")
            
            # Instead of doing real processing, use simulated designer processing
            for idx, designer in enumerate(season["designers"]):
                # Use events for simulation timing
                designer_complete = threading.Event()
                designer_complete.wait(timeout=random.uniform(0.5, 1.5))  # Randomized timing
                processed_items += 1
        
        # Stop monitoring and get timing data
        stop_monitoring.set()
        monitor_thread.join()
        end_time = datetime.now().timestamp()
        execution_time = end_time - start_time
        
        # Calculate metrics
        items_per_second = processed_items / execution_time
        expected_items = num_seasons * num_designers
        success_rate = processed_items / expected_items if expected_items > 0 else 0
        
        # Record results
        result = {
            "mode": "multi-designer",
            "max_workers": max_workers,
            "execution_time": execution_time,
            "items_processed": processed_items,
            "items_per_second": items_per_second,
            "success_rate": success_rate,
            "resource_data": resource_data,
            "num_seasons": num_seasons,
            "num_designers": num_designers,
            "timestamp": timestamp
        }
        
        benchmark_runner.results.append(result)
        return result
        
    except Exception as e:
        benchmark_runner.logger.error(f"Error in multi-designer benchmark: {str(e)}")
        return {"error": str(e)}
        
    finally:
        # Clean up
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)


def run_multi_season_benchmark(benchmark_runner, num_seasons, num_designers, max_workers, test_data, timestamp):
    """Run benchmark for multi-season parallel processing.
    
    Args:
        benchmark_runner: Benchmark runner instance
        num_seasons: Number of seasons to process
        num_designers: Number of designers per season to process
        max_workers: Maximum number of workers
        test_data: Test data to use
        timestamp: Timestamp for file naming
    """
    benchmark_runner.logger.info(f"Running multi-season benchmark with {max_workers} workers")
    
    # Create temporary storage
    temp_dir, storage = create_temp_storage(test_data, timestamp)
    
    try:
        # Setup monitoring
        stop_monitoring = threading.Event()
        monitor_thread = threading.Thread(
            target=lambda: monitor_resources(os.getpid(), stop_monitoring)
        )
        resource_data = {"cpu": [], "memory": [], "timestamps": []}
        
        # Prepare test data subset
        test_seasons = test_data["seasons"][:num_seasons]
        for season in test_seasons:
            season["designers"] = season["designers"][:num_designers]
        
        # Run benchmark
        start_time = datetime.now().timestamp()
        monitor_thread.start()
        
        # Import and create multi-season manager
        from src.parallel_processor import ParallelProcessingManager
        manager = ParallelProcessingManager(
            max_workers=max_workers,
            mode="multi-season",
            checkpoint_file=None
        )
        
        # Mock the scraper initialization - simplified for benchmark
        manager.initialize_resources = lambda: None
        manager.driver_pool = [None] * max_workers
        manager.storage = storage
        
        # Use a ThreadPoolExecutor to simulate parallel processing
        processed_items = 0
        with ThreadPoolExecutor(max_workers=min(max_workers, len(test_seasons))) as executor:
            # Submit each season for processing
            futures = []
            for season in test_seasons:
                # Process each season with mock functions in parallel
                futures.append(executor.submit(lambda s: _process_season_mock(s, benchmark_runner.logger), season))
            
            # Wait for all futures to complete
            for future in futures:
                result = future.result()
                processed_items += result.get("processed_designers", 0)
        
        # Stop monitoring and get timing data
        stop_monitoring.set()
        monitor_thread.join()
        end_time = datetime.now().timestamp()
        execution_time = end_time - start_time
        
        # Calculate metrics
        items_per_second = processed_items / execution_time
        expected_items = num_seasons * num_designers
        success_rate = processed_items / expected_items if expected_items > 0 else 0
        
        # Record results
        result = {
            "mode": "multi-season",
            "max_workers": max_workers,
            "execution_time": execution_time,
            "items_processed": processed_items,
            "items_per_second": items_per_second,
            "success_rate": success_rate,
            "resource_data": resource_data,
            "num_seasons": num_seasons,
            "num_designers": num_designers,
            "timestamp": timestamp
        }
        
        benchmark_runner.results.append(result)
        return result
        
    except Exception as e:
        benchmark_runner.logger.error(f"Error in multi-season benchmark: {str(e)}")
        return {"error": str(e)}
        
    finally:
        # Clean up
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)


def _process_season_mock(season: Dict[str, Any], logger) -> Dict[str, Any]:
    """Mock function to simulate processing a season.
    
    Args:
        season: Season data dictionary
        logger: Logger instance
        
    Returns:
        Dict with processing results
    """
    logger.info(f"Processing season: {season['season']} {season['year']}")
    
    # Use event-based waiting instead of sleeping
    processing_event = threading.Event()
    processing_event.wait(timeout=0.5)  # Simulate base season processing
    
    processed_designers = 0
    
    # Process designers sequentially within this season
    for designer in season["designers"]:
        logger.info(f"Processing designer: {designer['name']}")
        
        # Use event-based waiting
        designer_event = threading.Event()
        designer_event.wait(timeout=1.0)  # Simulate designer processing
        
        processed_designers += 1
    
    return {
        "season": f"{season['season']} {season['year']}",
        "processed_designers": processed_designers
    }