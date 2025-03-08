"""Core utilities for parallel processing in the Vogue Runway scraper.

This module provides foundational utility functions that support parallel processing,
including browser authentication sharing, retry logic, and event-based coordination.
"""

import logging
import threading
import random
import functools
from concurrent.futures import ThreadPoolExecutor
import queue

from selenium.webdriver.remote.webdriver import WebDriver

from ..utils.wait_utils import wait_for_page_load, EventBasedWait


def share_authentication(main_driver: WebDriver, new_driver: WebDriver, logger: logging.Logger, base_url: str) -> bool:
    """
    Share authentication cookies from main driver to new driver instances.
    
    Args:
        main_driver: Source WebDriver with authenticated session
        new_driver: Target WebDriver to receive cookies
        logger: Logger instance for tracking
        base_url: Base URL for the site
        
    Returns:
        bool: True if authentication sharing successful
    """
    try:
        # First navigate to the base domain in the new driver
        new_driver.get(base_url)
        
        # Wait for page to load before adding cookies
        wait_for_page_load(new_driver, timeout=10)
        
        # Get cookies from authenticated session
        cookies = main_driver.get_cookies()
        
        # Apply cookies to new driver
        for cookie in cookies:
            try:
                new_driver.add_cookie(cookie)
            except Exception as e:
                logger.warning(f"Could not add cookie {cookie.get('name')}: {str(e)}")
        
        # Refresh to apply cookies
        new_driver.refresh()
        
        # Wait for page to load after refresh
        wait_for_page_load(new_driver, timeout=10)
        
        # Verify authentication
        from src.handlers.auth import VogueAuthHandler
        auth_handler = VogueAuthHandler(new_driver, logger, base_url)
        if not auth_handler.verify_authentication():
            logger.warning("Authentication sharing may have failed, attempting direct authentication")
            
            # Try direct authentication as fallback
            from src.config.settings import AUTH_URL
            auth_handler.authenticate(AUTH_URL)
            
        logger.info("Successfully shared authentication to new driver")
        return True
        
    except Exception as e:
        logger.error(f"Error sharing authentication: {str(e)}")
        return False


def with_retry(func=None, *, max_retries=3, retry_delay=2):
    """Decorator to add retry capability to any function.
    
    Args:
        func: Function to decorate
        max_retries: Maximum number of retry attempts
        retry_delay: Base delay between retries in seconds
        
    Returns:
        Decorated function with retry capability
    
    Example:
        @with_retry(max_retries=3, retry_delay=1)
        def fetch_data():
            # operation that might fail
            return data
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            attempt = 0
            last_exception = None
            
            while attempt < max_retries:
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    attempt += 1
                    
                    if attempt < max_retries:
                        # Calculate backoff with jitter
                        delay = retry_delay * (2 ** (attempt - 1))
                        jitter = random.uniform(0.8, 1.2)
                        
                        # Use event-based waiting
                        EventBasedWait.wait(delay * jitter)
            
            # Re-raise the last exception after all retries fail
            if last_exception:
                raise last_exception
        return wrapper
    
    if func is None:
        return decorator
    return decorator(func)


class ParallelTaskCoordinator:
    """Coordinates parallel tasks with efficient waiting and synchronization."""
    
    def __init__(self, max_workers: int, logger: logging.Logger):
        """Initialize coordinator with maximum worker count."""
        self.max_workers = max_workers
        self.logger = logger
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks = {}
        self.results = queue.Queue()
        self.errors = queue.Queue()
        self.completion_event = threading.Event()
        self.task_count = 0
        self.completed_count = 0
        self.lock = threading.RLock()
    
    def add_task(self, task_func, *args, **kwargs):
        """Add a task to be executed in parallel."""
        with self.lock:
            task_id = self.task_count
            self.task_count += 1
            
            # Wrap task to capture results and errors
            def wrapped_task():
                try:
                    result = task_func(*args, **kwargs)
                    self.results.put((task_id, result))
                    with self.lock:
                        self.completed_count += 1
                        if self.completed_count >= self.task_count:
                            self.completion_event.set()
                    return result
                except Exception as e:
                    self.logger.error(f"Task {task_id} failed: {str(e)}")
                    self.errors.put((task_id, str(e)))
                    with self.lock:
                        self.completed_count += 1
                        if self.completed_count >= self.task_count:
                            self.completion_event.set()
            
            # Submit task to executor
            future = self.executor.submit(wrapped_task)
            self.tasks[task_id] = future
            return task_id
    
    def wait_for_completion(self, timeout=None):
        """Wait for all tasks to complete with timeout."""
        return self.completion_event.wait(timeout=timeout)
    
    def wait_for_next_result(self, timeout=None):
        """Wait for the next result to be available."""
        try:
            return self.results.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_all_results(self):
        """Get all available results without waiting."""
        results = []
        while not self.results.empty():
            results.append(self.results.get())
        return results
    
    def get_all_errors(self):
        """Get all available errors without waiting."""
        errors = []
        while not self.errors.empty():
            errors.append(self.errors.get())
        return errors
    
    def shutdown(self, wait=True):
        """Shutdown the executor."""
        self.executor.shutdown(wait=wait)