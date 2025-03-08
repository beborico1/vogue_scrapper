# handlers/images/operation_handler.py
"""Operation handlers with retry logic for image collection.

This module provides robust retry mechanisms:
- Exponential backoff
- Operation validation
- Error handling
"""

from typing import Any, Callable, Optional
from logging import Logger
from functools import wraps
import time
import random
import threading

from ...config.settings import RETRY_ATTEMPTS, RETRY_DELAY


def retry_operation(logger: Logger, operation: Callable, operation_name: str) -> Any:
    """Retry an operation with exponential backoff.

    Args:
        logger: Logger instance
        operation: Operation to retry
        operation_name: Name of the operation for logging

    Returns:
        Any: Result of the operation or None if failed
    """
    retry_count = 0
    max_delay = RETRY_DELAY * (2 ** (RETRY_ATTEMPTS - 1))
    
    while retry_count < RETRY_ATTEMPTS:
        try:
            result = operation()
            if result is not None:
                if retry_count > 0:
                    logger.info(f"Operation '{operation_name}' succeeded on attempt {retry_count + 1}")
                return result
        except Exception as e:
            logger.warning(
                f"Attempt {retry_count + 1} failed for {operation_name}: {str(e)}"
            )

        retry_count += 1
        if retry_count < RETRY_ATTEMPTS:
            # Calculate backoff with jitter
            delay = min(max_delay, RETRY_DELAY * (2 ** retry_count))
            jitter = random.uniform(0.8, 1.2)  # Add 20% jitter
            adjusted_delay = delay * jitter
            
            logger.info(f"Retrying {operation_name} in {adjusted_delay:.2f} seconds (attempt {retry_count + 1}/{RETRY_ATTEMPTS})")
            
            # Use an event for waiting instead of sleep
            retry_event = threading.Event()
            retry_event.wait(timeout=adjusted_delay)

    logger.error(f"All {RETRY_ATTEMPTS} retry attempts failed for {operation_name}")
    return None


def validate_operation(
    logger: Logger, 
    validation_func: Callable, 
    operation_name: str,
    max_attempts: Optional[int] = None,
    poll_interval: float = 0.5,
) -> bool:
    """Validate an operation with polling logic.
    
    Args:
        logger: Logger instance
        validation_func: Function that returns True if validation passes
        operation_name: Name of the operation for logging
        max_attempts: Maximum number of attempts (defaults to RETRY_ATTEMPTS)
        poll_interval: Time between polling attempts in seconds
        
    Returns:
        bool: True if validation passes
    """
    if max_attempts is None:
        max_attempts = RETRY_ATTEMPTS
        
    attempts = 0
    while attempts < max_attempts:
        try:
            if validation_func():
                return True
        except Exception as e:
            logger.warning(
                f"Validation attempt {attempts + 1} failed for {operation_name}: {str(e)}"
            )
            
        attempts += 1
        if attempts < max_attempts:
            # Use a short polling interval rather than exponential backoff for validation
            validation_wait = threading.Event()
            validation_wait.wait(timeout=poll_interval)
            
    logger.error(f"All {max_attempts} validation attempts failed for {operation_name}")
    return False


def safe_operation(logger: Logger, operation: Callable, default_value: Any = None) -> Any:
    """Execute an operation safely with error handling.
    
    Args:
        logger: Logger instance
        operation: Operation to execute
        default_value: Default value to return if operation fails
        
    Returns:
        Any: Result of the operation or default_value if failed
    """
    try:
        return operation()
    except Exception as e:
        logger.error(f"Operation failed: {str(e)}")
        return default_value


def with_retry(func=None, *, max_retries=RETRY_ATTEMPTS, retry_delay=RETRY_DELAY):
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
        @wraps(f)
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
                        wait_event = threading.Event()
                        wait_event.wait(timeout=delay * jitter)
            
            # Re-raise the last exception after all retries fail
            if last_exception:
                raise last_exception
        return wrapper
    
    if func is None:
        return decorator
    return decorator(func)