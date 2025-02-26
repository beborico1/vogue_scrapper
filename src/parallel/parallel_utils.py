"""Utility functions for parallel processing in the Vogue Runway scraper.

This module provides utility functions that support parallel processing,
including browser authentication sharing, resource management, and retry logic.
"""

# Import utilities from specialized modules
from .core_utils import share_authentication, with_retry
from .resource_utils import monitor_resources, ResourceMonitor
from .workload_utils import distribute_workload, run_in_parallel

# Re-export all utilities
__all__ = [
    'share_authentication',
    'with_retry',
    'monitor_resources',
    'ResourceMonitor',
    'distribute_workload',
    'run_in_parallel',
]