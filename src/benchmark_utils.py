#!/usr/bin/env python3
"""
Utility functions for benchmark testing.

This file provides backward compatibility for imports after code refactoring.
It re-exports all functionality from the new benchmark_utils package.
"""

# Re-export all functionality from the new package structure
from benchmark_utils.core_utils import (
    monitor_resources, 
    calculate_benchmark_stats,
    format_execution_time,
    _process_season_mock
)

from benchmark_utils.parallel_processing import (
    create_temp_storage,
    run_multi_designer_benchmark,
    run_multi_season_benchmark
)

# For backward compatibility, ensure all original functions are available
__all__ = [
    'monitor_resources',
    'calculate_benchmark_stats',
    'format_execution_time',
    '_process_season_mock',
    'create_temp_storage',
    'run_multi_designer_benchmark',
    'run_multi_season_benchmark'
]