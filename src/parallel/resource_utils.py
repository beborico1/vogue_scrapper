# src/parallel/resource_utils.py
"""Resource monitoring utilities for parallel processing.

This module provides utilities for monitoring CPU and memory usage
during parallel processing operations.
"""

import threading
import logging
from typing import Dict, List, Optional, Any
import time


def monitor_resources(pid: int, stop_event: threading.Event, interval: float = 0.5) -> Dict[str, List[float]]:
    """
    Monitor CPU and memory usage of a process.
    
    Args:
        pid: Process ID to monitor
        stop_event: Event to signal when monitoring should stop
        interval: Sampling interval in seconds
        
    Returns:
        Dict with CPU and memory usage data
    """
    try:
        import psutil
        
        process = psutil.Process(pid)
        cpu_usage = []
        memory_usage = []
        timestamps = []
        
        start_time = time.time()
        
        while not stop_event.wait(interval):  # Use wait instead of set+sleep for cleaner polling
            try:
                # Get CPU and memory usage
                cpu_percent = process.cpu_percent(interval=0.1)
                memory_percent = process.memory_percent()
                
                # Add to lists
                cpu_usage.append(cpu_percent)
                memory_usage.append(memory_percent)
                timestamps.append(time.time() - start_time)
                
            except Exception:
                # Process might have ended
                break
        
        return {
            "cpu": cpu_usage,
            "memory": memory_usage,
            "timestamps": timestamps
        }
        
    except ImportError:
        # psutil not available
        return {"cpu": [], "memory": [], "timestamps": []}
    except Exception:
        # Process not found or other error
        return {"cpu": [], "memory": [], "timestamps": []}


class ResourceMonitor:
    """Class to monitor resource usage during parallel processing."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the resource monitor.
        
        Args:
            logger: Optional logger for tracking
        """
        self.logger = logger
        self.monitoring_thread = None
        self.stop_event = None
        self.resource_data = None
    
    def start_monitoring(self) -> None:
        """Start monitoring resource usage."""
        try:
            import os
            import psutil
            
            # Create stop event
            self.stop_event = threading.Event()
            
            # Get current process ID
            pid = os.getpid()
            
            # Start monitoring thread
            self.monitoring_thread = threading.Thread(
                target=self._monitor_resources,
                args=(pid,)
            )
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
            
            if self.logger:
                self.logger.info(f"Resource monitoring started for process {pid}")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to start resource monitoring: {str(e)}")
    
    def stop_monitoring(self) -> Dict[str, List[float]]:
        """Stop monitoring and return collected data.
        
        Returns:
            Dict with CPU and memory usage data
        """
        if self.stop_event:
            self.stop_event.set()
            
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2)
            
        if self.logger:
            self.logger.info("Resource monitoring stopped")
            
        return self.resource_data or {"cpu": [], "memory": [], "timestamps": []}
    
    def _monitor_resources(self, pid: int) -> None:
        """Internal method to monitor resources.
        
        Args:
            pid: Process ID to monitor
        """
        try:
            import psutil
            
            process = psutil.Process(pid)
            cpu_usage = []
            memory_usage = []
            timestamps = []
            
            start_time = time.time()
            
            while not self.stop_event.wait(0.5):  # Use wait instead of set+sleep
                try:
                    # Get CPU and memory usage
                    cpu_percent = process.cpu_percent(interval=0.1)
                    memory_percent = process.memory_percent()
                    
                    # Add to lists
                    cpu_usage.append(cpu_percent)
                    memory_usage.append(memory_percent)
                    timestamps.append(time.time() - start_time)
                    
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error in resource monitoring: {str(e)}")
                    break
            
            # Store collected data
            self.resource_data = {
                "cpu": cpu_usage,
                "memory": memory_usage,
                "timestamps": timestamps
            }
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Resource monitoring failed: {str(e)}")
            self.resource_data = {"cpu": [], "memory": [], "timestamps": []}