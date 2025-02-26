#!/usr/bin/env python3
"""
Visualizations for benchmark results.

This module provides functionality for generating visualizations from benchmark data,
including execution time comparisons, throughput charts, and resource usage graphs.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Any
from pathlib import Path
import logging

from src.utils.logging import setup_logger


class BenchmarkVisualizer:
    """Handles visualization of benchmark results."""
    
    def __init__(self, output_dir: Path, timestamp: str):
        """Initialize the visualizer.
        
        Args:
            output_dir: Directory to save visualizations
            timestamp: Timestamp for this benchmark run
        """
        self.logger = setup_logger()
        self.output_dir = output_dir
        self.timestamp = timestamp
        
        # Create plots directory if it doesn't exist
        self.plots_dir = output_dir / "plots"
        self.plots_dir.mkdir(exist_ok=True)
    
    def generate_visualizations(self, results: List[Dict[str, Any]]) -> None:
        """Generate visualizations of benchmark results.
        
        Args:
            results: List of benchmark result dictionaries
        """
        if not results:
            self.logger.warning("No benchmark results to visualize")
            return
        
        # Generate execution time comparison plot
        self._generate_execution_time_plot(results)
        
        # Generate items per second comparison plot
        self._generate_throughput_plot(results)
        
        # Generate resource usage plots for each benchmark
        for result in results:
            if "resource_data" in result:
                self._generate_resource_plot(result)
        
        self.logger.info(f"Generated benchmark visualizations in {self.plots_dir}")
    
    def _generate_execution_time_plot(self, results: List[Dict[str, Any]]) -> None:
        """Generate execution time comparison plot.
        
        Args:
            results: List of benchmark result dictionaries
        """
        plt.figure(figsize=(10, 6))
        
        # Group results by mode
        modes = {}
        for result in results:
            mode = result["mode"]
            if mode not in modes:
                modes[mode] = []
            modes[mode].append(result)
        
        # Plot execution times
        x_labels = []
        bar_width = 0.25
        index = np.arange(len(modes))
        
        for i, (mode, mode_results) in enumerate(modes.items()):
            times = [r["execution_time"] for r in mode_results]
            workers = [r.get("max_workers", 1) for r in mode_results]
            
            # Sort by worker count
            sorted_data = sorted(zip(workers, times))
            if sorted_data:
                workers, times = zip(*sorted_data)
            else:
                workers, times = [], []
            
            # Create bars with different positions based on mode
            bars = plt.bar(index + i*bar_width, times, bar_width, label=f"{mode}")
            
            # Add worker counts as labels
            for bar, worker in zip(bars, workers):
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f"{worker} workers" if worker > 1 else "sequential",
                        ha='center', va='bottom', rotation=0)
            
            # Add mode to labels
            if mode not in x_labels:
                x_labels.append(mode)
        
        plt.xlabel('Processing Mode')
        plt.ylabel('Execution Time (seconds)')
        plt.title('Execution Time Comparison by Processing Mode')
        plt.xticks(index + bar_width/2, x_labels)
        plt.legend()
        plt.tight_layout()
        
        # Save plot
        plt.savefig(self.plots_dir / f"execution_time_comparison_{self.timestamp}.png")
        plt.close()
    
    def _generate_throughput_plot(self, results: List[Dict[str, Any]]) -> None:
        """Generate items per second (throughput) comparison plot.
        
        Args:
            results: List of benchmark result dictionaries
        """
        plt.figure(figsize=(10, 6))
        
        # Group results by mode
        modes = {}
        for result in results:
            mode = result["mode"]
            if mode not in modes:
                modes[mode] = []
            modes[mode].append(result)
        
        # Plot throughput
        x_labels = []
        bar_width = 0.25
        index = np.arange(len(modes))
        
        for i, (mode, mode_results) in enumerate(modes.items()):
            throughput = [r["items_per_second"] for r in mode_results]
            workers = [r.get("max_workers", 1) for r in mode_results]
            
            # Sort by worker count
            sorted_data = sorted(zip(workers, throughput))
            if sorted_data:
                workers, throughput = zip(*sorted_data)
            else:
                workers, throughput = [], []
            
            # Create bars with different positions based on mode
            bars = plt.bar(index + i*bar_width, throughput, bar_width, label=f"{mode}")
            
            # Add worker counts as labels
            for bar, worker in zip(bars, workers):
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f"{worker} workers" if worker > 1 else "sequential",
                        ha='center', va='bottom', rotation=0)
            
            # Add mode to labels
            if mode not in x_labels:
                x_labels.append(mode)
        
        plt.xlabel('Processing Mode')
        plt.ylabel('Items Processed per Second')
        plt.title('Throughput Comparison by Processing Mode')
        plt.xticks(index + bar_width/2, x_labels)
        plt.legend()
        plt.tight_layout()
        
        # Save plot
        plt.savefig(self.plots_dir / f"throughput_comparison_{self.timestamp}.png")
        plt.close()
    
    def _generate_resource_plot(self, result: Dict[str, Any]) -> None:
        """Generate resource usage plot for a benchmark result.
        
        Args:
            result: Benchmark result with resource data
        """
        if "resource_data" not in result or not result["resource_data"]:
            return
        
        resource_data = result["resource_data"]
        if not all(key in resource_data for key in ["cpu", "memory", "timestamps"]):
            return
        
        # Create plot
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
        
        # Plot CPU usage
        ax1.plot(resource_data["timestamps"], resource_data["cpu"], label="CPU Usage (%)")
        ax1.set_ylabel('CPU Usage (%)')
        ax1.set_title(f'Resource Usage - {result["mode"]} with {result.get("max_workers", 1)} workers')
        ax1.grid(True)
        ax1.legend()
        
        # Plot memory usage
        ax2.plot(resource_data["timestamps"], resource_data["memory"], label="Memory Usage (%)", color='green')
        ax2.set_xlabel('Time (seconds)')
        ax2.set_ylabel('Memory Usage (%)')
        ax2.grid(True)
        ax2.legend()
        
        plt.tight_layout()
        
        # Save plot
        mode = result["mode"]
        workers = result.get("max_workers", 1)
        plt.savefig(self.plots_dir / f"resource_usage_{mode}_{workers}workers_{self.timestamp}.png")
        plt.close()