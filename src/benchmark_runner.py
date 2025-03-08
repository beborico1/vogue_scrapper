# src/benchmark_runner.py
#!/usr/bin/env python3
"""
Core benchmark runner for testing parallel processing strategies.

This script defines the main BenchmarkRunner class which orchestrates
benchmarks for different parallel processing approaches in the Vogue Runway scraper.
"""

import os
import sys
import json
import argparse
import threading
from typing import Dict, List, Any
from pathlib import Path
from datetime import datetime
import csv
import psutil

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logging import setup_logger
from src.benchmark_visualizer import BenchmarkVisualizer
from src.benchmark_utils import monitor_resources, create_temp_storage
from src.utils.wait_utils import wait_for_page_load


class BenchmarkRunner:
    """Runs benchmarks for different parallel processing strategies."""
    
    def __init__(self, output_dir: str = "benchmark_results", test_data_path: str = None):
        """Initialize the benchmark runner.
        
        Args:
            output_dir: Directory to save benchmark results
            test_data_path: Path to test data JSON file (optional)
        """
        self.logger = setup_logger()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize test data
        self.test_data_path = Path(test_data_path) if test_data_path else None
        self.test_data = self._load_test_data()
        
        # Initialize results storage
        self.results = []
        
        # Track process for resource usage monitoring
        self.process = psutil.Process(os.getpid())
        
        # Setup timestamp for this benchmark run
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create visualizer
        self.visualizer = BenchmarkVisualizer(self.output_dir, self.timestamp)
        
    def _load_test_data(self) -> Dict[str, Any]:
        """Load test data from file or use default test data.
        
        Returns:
            Dict with test data
        """
        if self.test_data_path and self.test_data_path.exists():
            self.logger.info(f"Loading test data from {self.test_data_path}")
            with open(self.test_data_path, 'r') as f:
                return json.load(f)
        else:
            self.logger.info("Using default test data")
            return self._generate_default_test_data()
    
    def _generate_default_test_data(self) -> Dict[str, Any]:
        """Generate default test data with synthetic seasons and designers.
        
        Returns:
            Dict with synthetic test data
        """
        # Generate 5 test seasons with 10 designers each
        seasons = []
        for i in range(1, 6):
            season = {
                "season": f"Test Season {i}",
                "year": f"202{i}",
                "url": f"https://example.com/season_{i}",
                "designers": []
            }
            
            for j in range(1, 11):
                designer = {
                    "name": f"Designer {i}_{j}",
                    "url": f"https://example.com/season_{i}/designer_{j}",
                }
                season["designers"].append(designer)
            
            seasons.append(season)
        
        return {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "description": "Synthetic test data for benchmarking"
            },
            "seasons": seasons
        }

    def run_sequential_benchmark(self, num_seasons: int = 3, num_designers: int = 5) -> Dict[str, Any]:
        """Run benchmark for sequential processing.
        
        Args:
            num_seasons: Number of seasons to process
            num_designers: Number of designers per season to process
            
        Returns:
            Dict with benchmark results
        """
        self.logger.info(f"Running sequential benchmark with {num_seasons} seasons, {num_designers} designers each")
        
        # Create temporary storage
        temp_dir, storage = create_temp_storage(self.test_data, self.timestamp)
        
        try:
            # Setup monitoring
            stop_monitoring = threading.Event()
            monitor_thread = threading.Thread(
                target=lambda: monitor_resources(os.getpid(), stop_monitoring)
            )
            resource_data = {"cpu": [], "memory": [], "timestamps": []}
            
            # Prepare test data subset
            test_seasons = self.test_data["seasons"][:num_seasons]
            for season in test_seasons:
                season["designers"] = season["designers"][:num_designers]
            
            # Run benchmark
            start_time = datetime.now().timestamp()
            monitor_thread.start()
            
            # Sequential processing simulation
            processed_items = 0
            for season in test_seasons:
                # Simulate season processing
                self.logger.info(f"Processing season: {season['season']} {season['year']}")
                
                # Use events for simulation timing instead of sleep
                processing_complete = threading.Event()
                threading.Timer(0.5, processing_complete.set).start()  # Simulate base season processing time
                processing_complete.wait()  # Wait for the timer to complete
                
                for designer in season["designers"]:
                    # Simulate designer processing
                    self.logger.info(f"Processing designer: {designer['name']}")
                    
                    # Use events for simulation timing
                    designer_complete = threading.Event()
                    threading.Timer(1.0, designer_complete.set).start()  # Simulate designer processing time
                    designer_complete.wait()  # Wait for the timer to complete
                    
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
                "mode": "sequential",
                "execution_time": execution_time,
                "items_processed": processed_items,
                "items_per_second": items_per_second,
                "success_rate": success_rate,
                "resource_data": resource_data,
                "num_seasons": num_seasons,
                "num_designers": num_designers,
                "timestamp": self.timestamp
            }
            
            self.results.append(result)
            return result
            
        finally:
            # Clean up
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)

    def run_all_benchmarks(self, num_seasons: int = 3, num_designers: int = 10, 
                          workers_list: List[int] = [2, 4, 8]) -> None:
        """Run all benchmark tests with various configurations.
        
        Args:
            num_seasons: Number of seasons to process
            num_designers: Number of designers per season to process
            workers_list: List of worker counts to test
        """
        self.logger.info("Running all benchmarks")
        
        # Run sequential benchmark (baseline)
        self.run_sequential_benchmark(num_seasons, num_designers)
        
        # Import these here to avoid circular imports
        from src.benchmark_utils import run_multi_designer_benchmark, run_multi_season_benchmark
        
        # Run multi-designer benchmarks with different worker counts
        for workers in workers_list:
            run_multi_designer_benchmark(
                self, num_seasons, num_designers, workers, 
                self.test_data, self.timestamp
            )
        
        # Run multi-season benchmarks with different worker counts
        for workers in workers_list:
            run_multi_season_benchmark(
                self, num_seasons, num_designers, workers,
                self.test_data, self.timestamp
            )
        
        # Save and visualize results
        self.save_results()
        self.visualizer.generate_visualizations(self.results)
    
    def save_results(self) -> None:
        """Save benchmark results to files."""
        if not self.results:
            self.logger.warning("No benchmark results to save")
            return
        
        # Save as JSON
        json_path = self.output_dir / f"benchmark_results_{self.timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Save as CSV
        csv_path = self.output_dir / f"benchmark_results_{self.timestamp}.csv"
        with open(csv_path, 'w', newline='') as f:
            fieldnames = [
                "mode", "max_workers", "execution_time", "items_processed", 
                "items_per_second", "success_rate", "num_seasons", "num_designers"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in self.results:
                # Extract only the fields we want for the CSV
                row = {field: result.get(field, "") for field in fieldnames}
                writer.writerow(row)
        
        self.logger.info(f"Saved benchmark results to {json_path} and {csv_path}")