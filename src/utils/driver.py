"""
Browser driver configuration and setup utilities.

This module provides utilities for setting up and configuring the Chrome WebDriver
with custom options from the configuration settings.
"""

from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager

from ..config.settings import config

def setup_chrome_driver() -> WebDriver:
    """
    Configure and initialize Chrome WebDriver with custom options.
    
    Uses configuration settings from the config module to set up the browser
    with appropriate options, user agent, and wait times.
    
    Returns:
        WebDriver: Configured Chrome WebDriver instance
        
    Example:
        driver = setup_chrome_driver()
        try:
            # Use the driver
            driver.get("https://www.example.com")
        finally:
            driver.quit()
    """
    # Create Chrome options
    chrome_options = _create_chrome_options()
    # Initialize the Chrome driver with configured options
    driver = _initialize_driver(chrome_options)

    # Configure driver settings
    _configure_driver(driver)
    
    return driver

def _create_chrome_options() -> Options:
    """
    Create and configure Chrome options from settings.
    
    Returns:
        Options: Configured Chrome options
    """
    chrome_options = Options()
    
    # Add custom user agent
    if 'user_agent' in config.chrome_options:
        chrome_options.add_argument(
            f'--user-agent={config.chrome_options["user_agent"]}'
        )
    
    # Add window size configuration
    if 'window_size' in config.chrome_options:
        chrome_options.add_argument(config.chrome_options["window_size"])
    
    # Add notifications configuration
    if 'notifications' in config.chrome_options:
        chrome_options.add_argument(config.chrome_options["notifications"])
    
    return chrome_options

def _initialize_driver(options: Options) -> WebDriver:
    """
    Initialize Chrome WebDriver with given options.
    
    Args:
        options: Configured Chrome options
        
    Returns:
        WebDriver: Initialized Chrome WebDriver
    """
    print("10") # ... remove
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

def _configure_driver(driver: WebDriver) -> None:
    """
    Configure WebDriver settings.
    
    Args:
        driver: Chrome WebDriver instance to configure
    """
    # Set implicit wait time from configuration
    driver.implicitly_wait(config.browser.IMPLICIT_WAIT)