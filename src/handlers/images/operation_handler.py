# handlers/images/operation_handler.py
"""Operation handlers with retry logic for image collection.

This module provides robust retry mechanisms:
- Exponential backoff
- Operation validation
- Error handling
"""

import time
from typing import Any, Callable, Optional
from logging import Logger

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
    while retry_count < RETRY_ATTEMPTS:
        try:
            result = operation()
            if result is not None:
                return result
        except Exception as e:
            logger.warning(
                f"Attempt {retry_count + 1} failed for {operation_name}: {str(e)}"
            )

        retry_count += 1
        if retry_count < RETRY_ATTEMPTS:
            time.sleep(RETRY_DELAY * (2**retry_count))

    logger.error(f"All retry attempts failed for {operation_name}")
    return None


def validate_operation(
    logger: Logger, 
    validation_func: Callable, 
    operation_name: str,
    max_attempts: Optional[int] = None
) -> bool:
    """Validate an operation with retry logic.
    
    Args:
        logger: Logger instance
        validation_func: Function that returns True if validation passes
        operation_name: Name of the operation for logging
        max_attempts: Maximum number of attempts (defaults to RETRY_ATTEMPTS)
        
    Returns:
        bool: True if validation passes
    """
    if max_attempts is None:
        max_attempts = RETRY_ATTEMPTS
        
    retry_count = 0
    while retry_count < max_attempts:
        try:
            if validation_func():
                return True
        except Exception as e:
            logger.warning(
                f"Validation attempt {retry_count + 1} failed for {operation_name}: {str(e)}"
            )
            
        retry_count += 1
        if retry_count < max_attempts:
            time.sleep(RETRY_DELAY * (2**retry_count))
            
    logger.error(f"All validation attempts failed for {operation_name}")
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