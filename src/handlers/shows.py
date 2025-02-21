# handlers/shows.py
"""Enhanced shows handler implementation for Vogue Runway scraper."""

from typing import Optional
import time
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

from ..config.settings import PAGE_LOAD_WAIT
from ..exceptions.errors import ElementNotFoundError


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
            # Navigate to designer page
            self.driver.get(designer_url)
            time.sleep(PAGE_LOAD_WAIT)

            # Find the gallery section
            gallery = WebDriverWait(self.driver, PAGE_LOAD_WAIT).until(
                EC.presence_of_element_located((By.CLASS_NAME, "RunwayShowPageGalleryCta-fmTQJF"))
            )

            # Scroll to gallery to ensure button is in view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", gallery)
            time.sleep(2)  # Allow time for any dynamic content to load

            # Find and click the "View Slideshow" button
            button = WebDriverWait(self.driver, PAGE_LOAD_WAIT).until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        'a[href*="/slideshow/collection"] .button--primary span.button__label',
                    )
                )
            )

            # Try regular click first, fall back to JavaScript click if needed
            try:
                button.click()
            except ElementClickInterceptedException:
                self.logger.warning("Direct click failed, trying JavaScript click")
                self.driver.execute_script("arguments[0].click();", button)

            # Wait for navigation and get new URL
            time.sleep(PAGE_LOAD_WAIT)
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
            # Check for slideshow-specific elements
            WebDriverWait(self.driver, PAGE_LOAD_WAIT).until(
                EC.presence_of_all_elements_located(
                    [
                        (By.CLASS_NAME, "RunwayGalleryImageCollection"),
                        (By.CSS_SELECTOR, '[data-testid="RunwayGalleryControlNext"]'),
                        (By.CLASS_NAME, "RunwayGalleryLookNumberText-hidXa"),
                    ]
                )
            )
            return True

        except (TimeoutException, NoSuchElementException):
            return False
