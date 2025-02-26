# Step 1: Modify src/parallel/__init__.py
# Remove the direct import of ParallelProcessingManager

"""
Parallel processing package for Vogue Runway scraper.

This package provides functionality for parallel processing of seasons,
designers, and looks during the scraping process. It includes:

1. Multi-season parallelism - Process multiple seasons concurrently
2. Multi-designer parallelism - Process multiple designers within a season concurrently
3. Multi-look parallelism - Process multiple looks for a designer concurrently

Each approach has different trade-offs in terms of resource usage and efficiency.
"""

# Import processor functions
from src.parallel.parallel_season_processor import process_single_season
from src.parallel.parallel_designer_processor import process_single_designer
from src.parallel.parallel_look_processor import ParallelLookScraper
from src.parallel.parallel_look_batch import process_looks_batch

# Import specialized parallel processing methods
from src.parallel.processor_methods import process_designers_parallel, process_multiple_seasons_parallel
from src.parallel.processor_looks import process_looks_parallel

# Import utility functions
from src.parallel.parallel_utils import (
    share_authentication,
    with_retry,
    distribute_workload,
    run_in_parallel,
    ResourceMonitor
)

__all__ = [
    'process_single_season',
    'process_single_designer',
    'ParallelLookScraper',
    'process_looks_batch',
    'process_designers_parallel',
    'process_multiple_seasons_parallel',
    'process_looks_parallel',
    'share_authentication',
    'with_retry',
    'distribute_workload',
    'run_in_parallel',
    'ResourceMonitor'
]

# Note: We've removed the direct import of ParallelProcessingManager
# to avoid the circular import