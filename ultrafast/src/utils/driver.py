"""
Browser driver utilities for Ultrafast Vogue Scraper.

This module provides utilities for setting up and configuring the Chrome WebDriver
in non-headless mode to enable visual monitoring of the scraping process.
"""

from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager

from ..config.settings import Config


def setup_chrome_driver(config: Config) -> WebDriver:
    """
    Configure and initialize Chrome WebDriver in non-headless mode.
    
    Args:
        config: Configuration instance with browser settings
    
    Returns:
        WebDriver: Configured Chrome WebDriver instance
    """
    # Create and configure Chrome options
    chrome_options = Options()
    
    # Add custom user agent
    chrome_options.add_argument(f'--user-agent={config.browser.USER_AGENT}')
    
    # Add window size configuration (maximize for visibility)
    chrome_options.add_argument(config.browser.WINDOW_SIZE)
    
    # Disable notifications
    chrome_options.add_argument(config.browser.DISABLE_NOTIFICATIONS)

    # Add timeout settings
    chrome_options.add_argument("--dns-prefetch-disable")
    
    # Try to initialize Chrome driver with retries
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # Initialize Chrome driver with options
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()), 
                options=chrome_options
            )
            
            # Set implicit wait time for element searches
            driver.implicitly_wait(config.browser.IMPLICIT_WAIT)
            
            # Set page load timeout
            driver.set_page_load_timeout(60)  # 60 seconds max for page loads
            
            return driver
            
        except Exception as e:
            if attempt < max_attempts - 1:
                print(f"Chrome driver initialization failed (attempt {attempt+1}): {str(e)}")
                print("Retrying in 5 seconds...")
                import time
                time.sleep(5)
            else:
                raise
    
    # This should never be reached due to the raise in the exception handler
    raise RuntimeError("Failed to initialize Chrome driver after multiple attempts")