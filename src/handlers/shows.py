"""Shows handling for Vogue Runway scraper."""

import time
from typing import Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException
)

from ..config.settings import PAGE_LOAD_WAIT, SELECTORS
from ..exceptions.errors import ElementNotFoundError

class VogueShowsHandler:
    """Handles show-related operations for Vogue Runway."""
    
    def __init__(self, driver, logger):
        """Initialize the shows handler."""
        self.driver = driver
        self.logger = logger

    def get_slideshow_url(self, designer_url: str) -> Optional[str]:
        """
        Navigate to designer page and get slideshow URL.
        
        Args:
            designer_url: URL of the designer's page
            
        Returns:
            Optional[str]: URL of the slideshow or None if not found
        """
        self.logger.info(f"Getting slideshow URL from designer page: {designer_url}")
        
        try:
            self.driver.get(designer_url)
            time.sleep(PAGE_LOAD_WAIT)
            
            # Wait for and click the slideshow button
            slideshow_button = self._find_slideshow_button()
            if not slideshow_button:
                raise ElementNotFoundError("Slideshow button not found")
                
            self._click_slideshow_button(slideshow_button)
            
            # Get the new URL after button click
            slideshow_url = self.driver.current_url
            self.logger.info(f"Found slideshow URL: {slideshow_url}")
            
            return slideshow_url
            
        except Exception as e:
            self.logger.error(f"Error getting slideshow URL: {str(e)}")
            return None

    def _find_slideshow_button(self):
        """Find the slideshow button element."""
        try:
            # Wait for button to be clickable
            wait = WebDriverWait(self.driver, PAGE_LOAD_WAIT)
            button = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'span.button__label')
                )
            )
            return button
        except TimeoutException:
            self.logger.warning("Timeout waiting for slideshow button")
            return None

    def _click_slideshow_button(self, button):
        """Attempt to click the slideshow button."""
        try:
            button.click()
            time.sleep(PAGE_LOAD_WAIT)  # Wait for navigation
        except ElementClickInterceptedException:
            # If direct click fails, try JavaScript click
            self.logger.warning("Direct click failed, trying JavaScript click")
            self.driver.execute_script("arguments[0].click();", button)
            time.sleep(PAGE_LOAD_WAIT)