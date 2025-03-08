# handlers/shows.py
"""Enhanced shows handler implementation for Vogue Runway scraper."""

from typing import Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
)
from selenium.webdriver.remote.webdriver import WebDriver
from logging import Logger

from ..config.settings import PAGE_LOAD_WAIT, ELEMENT_WAIT
from ..exceptions.errors import ElementNotFoundError
from ..utils.wait_utils import (
    wait_for_page_load, 
    wait_for_element_presence, 
    wait_for_element_clickable,
    wait_for_url_change
)


class VogueShowsHandler:
    """Handles show-related operations for Vogue Runway scraper."""

    def __init__(self, driver: WebDriver, logger: Logger):
        """Initialize the shows handler.

        Args:
            driver: Selenium WebDriver instance
            logger: Logger instance
        """
        self.driver = driver
        self.logger = logger

    def get_slideshow_url(self, designer_url: str) -> Optional[str]:
        """Navigate to designer page and enter slideshow view.

        Args:
            designer_url: URL of the designer's page

        Returns:
            Optional[str]: URL of the slideshow view after navigation or None if failed
        """
        self.logger.info(f"Navigating to designer page: {designer_url}")

        try:
            # Store initial URL for change detection
            initial_url = self.driver.current_url
            
            # Navigate to designer page
            self.driver.get(designer_url)
            
            # Wait for page to fully load
            wait_for_page_load(self.driver, timeout=PAGE_LOAD_WAIT)

            # Find the gallery section with proper wait
            gallery = wait_for_element_presence(
                self.driver, 
                (By.CLASS_NAME, "RunwayShowPageGalleryCta-fmTQJF"), 
                PAGE_LOAD_WAIT
            )
            
            if not gallery:
                self.logger.warning(f"Gallery section not found for: {designer_url}")
                return None

            # Scroll to gallery to ensure button is in view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", gallery)
            
            # Wait for the button to be in view and fully loaded
            WebDriverWait(self.driver, ELEMENT_WAIT).until(
                lambda d: d.execute_script(
                    "var rect = arguments[0].getBoundingClientRect(); " +
                    "return (rect.top >= 0 && rect.bottom <= window.innerHeight);",
                    gallery
                )
            )

            # Find and wait for the "View Slideshow" button to be clickable
            button = wait_for_element_clickable(
                self.driver,
                (By.CSS_SELECTOR, 'a[href*="/slideshow/collection"] .button--primary span.button__label'),
                ELEMENT_WAIT
            )
            
            if not button:
                self.logger.warning("View Slideshow button not found or not clickable")
                
                # Try fallback to first look thumbnail
                thumbnail = wait_for_element_clickable(
                    self.driver,
                    (By.CSS_SELECTOR, '.GridItem-buujkM a[href*="/slideshow/collection#1"]'),
                    ELEMENT_WAIT
                )
                
                if not thumbnail:
                    self.logger.error("No slideshow entry points found")
                    return None
                    
                button = thumbnail

            # Try regular click first, fall back to JavaScript click if needed
            try:
                button.click()
            except ElementClickInterceptedException:
                self.logger.warning("Direct click failed, trying JavaScript click")
                self.driver.execute_script("arguments[0].click();", button)

            # Wait for URL to change, indicating successful navigation
            url_changed = wait_for_url_change(self.driver, initial_url, PAGE_LOAD_WAIT)
            if not url_changed:
                self.logger.error("URL did not change after clicking slideshow button")
                return None
                
            # Wait for page to be fully loaded
            wait_for_page_load(self.driver, PAGE_LOAD_WAIT)
            
            # Verify we're in slideshow view
            if not self.verify_slideshow_view():
                self.logger.error("Failed to verify slideshow view")
                return None
                
            # Get the slideshow URL
            slideshow_url = self.driver.current_url
            self.logger.info(f"Successfully navigated to slideshow view: {slideshow_url}")
            return slideshow_url

        except Exception as e:
            self.logger.error(f"Failed to navigate to slideshow view: {str(e)}")
            return None

    def verify_slideshow_view(self) -> bool:
        """Verify that we're in slideshow view by checking for key elements.

        Returns:
            bool: True if in slideshow view, False otherwise
        """
        try:
            # Check for slideshow gallery element
            gallery_present = wait_for_element_presence(
                self.driver,
                (By.CLASS_NAME, "RunwayGalleryImageCollection"),
                ELEMENT_WAIT
            ) is not None
            
            if not gallery_present:
                return False
                
            # Check for navigation controls
            controls_present = wait_for_element_presence(
                self.driver,
                (By.CSS_SELECTOR, '[data-testid="RunwayGalleryControlNext"]'),
                ELEMENT_WAIT / 2  # Use shorter timeout for secondary check
            ) is not None
            
            # Check for look number indicator
            look_number_present = wait_for_element_presence(
                self.driver,
                (By.CLASS_NAME, "RunwayGalleryLookNumberText-hidXa"),
                ELEMENT_WAIT / 2  # Use shorter timeout for secondary check
            ) is not None
            
            return gallery_present and (controls_present or look_number_present)

        except Exception as e:
            self.logger.error(f"Error verifying slideshow view: {str(e)}")
            return False
            
    def extract_slideshow_url(self, designer_url: str) -> Optional[str]:
        """Extract the slideshow URL without navigating to it.
        
        This method only extracts the URL without clicking or navigating.
        
        Args:
            designer_url: URL of the designer's page
            
        Returns:
            Optional[str]: URL of the slideshow or None if not found
        """
        self.logger.info(f"Extracting slideshow URL from: {designer_url}")
        
        try:
            # Navigate to designer page
            self.driver.get(designer_url)
            
            # Wait for page to load
            wait_for_page_load(self.driver, timeout=PAGE_LOAD_WAIT)
            
            # Try to find the slideshow button
            slideshow_link = wait_for_element_presence(
                self.driver,
                (By.CSS_SELECTOR, 'a[href*="/slideshow/collection"]'),
                ELEMENT_WAIT
            )
            
            if slideshow_link:
                slideshow_url = slideshow_link.get_attribute("href")
                self.logger.info(f"Found slideshow URL: {slideshow_url}")
                return slideshow_url
            
            # Fallback: look for direct slideshow links in grid items
            grid_items = self.driver.find_elements(By.CSS_SELECTOR, '.GridItem-buujkM a[href*="/slideshow/collection"]')
            if grid_items:
                slideshow_url = grid_items[0].get_attribute("href")
                self.logger.info(f"Found slideshow URL from grid item: {slideshow_url}")
                return slideshow_url
                
            self.logger.warning(f"No slideshow URL found for: {designer_url}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting slideshow URL: {str(e)}")
            return None