# src/utils/wait_utils.py
"""
Wait utilities for dynamic waits instead of fixed sleeps.

This module provides standardized utility functions for waiting operations
that replace static calls with dynamic waits based on actual conditions.
"""

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import logging

from ..config.settings import PAGE_LOAD_WAIT, ELEMENT_WAIT


def wait_for_page_load(driver, timeout=PAGE_LOAD_WAIT):
    """Wait for page to fully load.
    
    Args:
        driver: WebDriver instance
        timeout: Maximum time to wait in seconds
        
    Returns:
        bool: True if page loaded successfully, False otherwise
    """
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        return True
    except TimeoutException:
        logging.getLogger(__name__).warning(f"Timeout waiting for page to load after {timeout}s")
        return False


def wait_for_url_change(driver, current_url, timeout=PAGE_LOAD_WAIT):
    """Wait for URL to change from the current one.
    
    Args:
        driver: WebDriver instance
        current_url: The URL to change from
        timeout: Maximum time to wait in seconds
        
    Returns:
        bool: True if URL changed, False otherwise
    """
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.current_url != current_url
        )
        return True
    except TimeoutException:
        logging.getLogger(__name__).warning(f"Timeout waiting for URL change after {timeout}s")
        return False


def wait_for_element_presence(driver, locator, timeout=ELEMENT_WAIT):
    """Wait for an element to be present in the DOM.
    
    Args:
        driver: WebDriver instance
        locator: Tuple of (By.X, "locator_string")
        timeout: Maximum time to wait in seconds
        
    Returns:
        WebElement if found, None otherwise
    """
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(locator)
        )
    except TimeoutException:
        logging.getLogger(__name__).warning(f"Timeout waiting for element {locator} after {timeout}s")
        return None


def wait_for_element_visibility(driver, locator, timeout=ELEMENT_WAIT):
    """Wait for an element to be visible.
    
    Args:
        driver: WebDriver instance
        locator: Tuple of (By.X, "locator_string")
        timeout: Maximum time to wait in seconds
        
    Returns:
        WebElement if visible, None otherwise
    """
    try:
        return WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located(locator)
        )
    except TimeoutException:
        logging.getLogger(__name__).warning(f"Timeout waiting for element visibility {locator} after {timeout}s")
        return None


def wait_for_element_clickable(driver, locator, timeout=ELEMENT_WAIT):
    """Wait for an element to be clickable.
    
    Args:
        driver: WebDriver instance
        locator: Tuple of (By.X, "locator_string")
        timeout: Maximum time to wait in seconds
        
    Returns:
        WebElement if clickable, None otherwise
    """
    try:
        return WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(locator)
        )
    except TimeoutException:
        logging.getLogger(__name__).warning(f"Timeout waiting for element to be clickable {locator} after {timeout}s")
        return None


def wait_for_staleness(driver, element, timeout=ELEMENT_WAIT):
    """Wait for an element to become stale (detached from DOM).
    
    Args:
        driver: WebDriver instance
        element: WebElement to check for staleness
        timeout: Maximum time to wait in seconds
        
    Returns:
        bool: True if element became stale, False otherwise
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.staleness_of(element)
        )
        return True
    except TimeoutException:
        logging.getLogger(__name__).warning("Timeout waiting for element staleness")
        return False


def wait_for_text_in_element(driver, locator, text, timeout=ELEMENT_WAIT):
    """Wait for specific text to be present in an element.
    
    Args:
        driver: WebDriver instance
        locator: Tuple of (By.X, "locator_string")
        text: Text to wait for
        timeout: Maximum time to wait in seconds
        
    Returns:
        WebElement if text found, None otherwise
    """
    try:
        return WebDriverWait(driver, timeout).until(
            EC.text_to_be_present_in_element(locator, text)
        )
    except TimeoutException:
        logging.getLogger(__name__).warning(f"Timeout waiting for text '{text}' in element {locator}")
        return None

# Add this class to the end of src/utils/wait_utils.py

import threading


class EventBasedWait:
    """Event-based waiting mechanism for parallel processing.
    
    This class provides a static method for waiting without using time.sleep(),
    which is safer for multi-threaded operations.
    """
    
    @staticmethod
    def wait(seconds: float) -> None:
        """Wait for the specified number of seconds using an event.
        
        Args:
            seconds: Time to wait in seconds
        """
        if seconds <= 0:
            return
            
        # Use event-based waiting instead of sleep
        wait_event = threading.Event()
        wait_event.wait(timeout=seconds)