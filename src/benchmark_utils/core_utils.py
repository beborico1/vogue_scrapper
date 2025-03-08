#!/usr/bin/env python3
"""
Utility functions for benchmark testing.

This module provides core utility functions for benchmark tests, including 
resource monitoring and general benchmark utilities.
"""

import threading
import logging
import psutil
from typing import Dict, List, Any, Tuple


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
        
        start_time = threading.Event().wait(0)  # Get current time without sleep
        
        while not stop_event.wait(interval):  # Use wait instead of set+sleep for cleaner polling
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


def _process_season_mock(season: Dict[str, Any], logger) -> Dict[str, Any]:
    """Mock function to simulate processing a season.
    
    Args:
        season: Season data dictionary
        logger: Logger instance
        
    Returns:
        Dict with processing results
    """
    logger.info(f"Processing season: {season['season']} {season['year']}")
    
    # Simulate base season processing using event-based waiting
    processing_event = threading.Event()
    processing_event.wait(timeout=0.5)
    
    processed_designers = 0
    
    # Process designers sequentially within this season
    for designer in season["designers"]:
        logger.info(f"Processing designer: {designer['name']}")
        
        # Simulate designer processing using event-based waiting
        designer_event = threading.Event()
        designer_event.wait(timeout=1.0)
        
        processed_designers += 1
    
    return {
        "season": f"{season['season']} {season['year']}",
        "processed_designers": processed_designers
    }


def calculate_benchmark_stats(results: Dict[str, Any], benchmark_type: str) -> Dict[str, Any]:
    """Calculate statistics for benchmark results.
    
    Args:
        results: Dictionary of benchmark results
        benchmark_type: Type of benchmark ('sequential', 'multi-designer', etc.)
        
    Returns:
        Dict with calculated statistics
    """
    stats = {
        "benchmark_type": benchmark_type,
        "total_time": results.get("execution_time", 0),
        "items_processed": results.get("items_processed", 0),
        "items_per_second": results.get("items_per_second", 0),
        "success_rate": results.get("success_rate", 0) * 100  # Convert to percentage
    }
    
    # Add CPU and memory stats if available
    if "resource_data" in results:
        resource_data = results["resource_data"]
        
        if resource_data.get("cpu"):
            stats["avg_cpu"] = sum(resource_data["cpu"]) / len(resource_data["cpu"]) if resource_data["cpu"] else 0
            stats["max_cpu"] = max(resource_data["cpu"]) if resource_data["cpu"] else 0
            
        if resource_data.get("memory"):
            stats["avg_memory"] = sum(resource_data["memory"]) / len(resource_data["memory"]) if resource_data["memory"] else 0
            stats["max_memory"] = max(resource_data["memory"]) if resource_data["memory"] else 0
    
    return stats


def format_execution_time(seconds: float) -> str:
    """Format execution time into human-readable format.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted time string
    """
    if seconds < 60:
        return f"{seconds:.2f} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{int(minutes)} min {int(remaining_seconds)} sec"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60
        return f"{int(hours)} hr {int(minutes)} min {int(remaining_seconds)} sec"