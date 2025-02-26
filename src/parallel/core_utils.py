"""Core utilities for parallel processing in the Vogue Runway scraper.

This module provides foundational utility functions that support parallel processing,
including browser authentication sharing and retry logic.
"""

import time
import logging
from typing import Dict, Any, Optional, List, Callable

from selenium.webdriver.remote.webdriver import WebDriver


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


def with_retry(operation: Callable, max_retries: int = 3, retry_delay: int = 2, 
               operation_name: str = "operation", logger: Optional[logging.Logger] = None) -> Any:
    """
    Execute an operation with automatic retry logic.
    
    Args:
        operation: Function to execute
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        operation_name: Name of the operation for logging
        logger: Optional logger for tracking
        
    Returns:
        Any: Result of the operation
        
    Raises:
        Exception: If all retry attempts fail
    """
    retry_count = 0
    last_exception = None
    
    while retry_count <= max_retries:
        try:
            result = operation()
            if result is not None:
                if logger:
                    logger.info(f"Successfully executed {operation_name} on attempt {retry_count + 1}")
                return result
                
        except Exception as e:
            last_exception = e
            if logger:
                logger.warning(f"Attempt {retry_count + 1}/{max_retries + 1} failed for {operation_name}: {str(e)}")
        
        # Increment retry count
        retry_count += 1
        
        # Break if max retries reached
        if retry_count > max_retries:
            break
        
        # Exponential backoff with jitter
        delay = retry_delay * (2 ** (retry_count - 1))
        if logger:
            logger.info(f"Retrying {operation_name} in {delay} seconds...")
        time.sleep(delay)
    
    # If we get here, all retries failed
    if logger:
        logger.error(f"All {max_retries + 1} attempts failed for {operation_name}")
    
    # Re-raise the last exception
    if last_exception:
        raise last_exception
    
    return None