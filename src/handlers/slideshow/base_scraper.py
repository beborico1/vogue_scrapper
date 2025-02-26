# src/handlers/slideshow/base_scraper.py
"""Base slideshow scraper with initialization and navigation functionality."""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException

class BaseSlideshowScraper:
    """Base class for slideshow scraping functionality."""

    def __init__(self, driver, logger, storage_handler):
        """Initialize the base slideshow scraper.
        
        Args:
            driver: Selenium WebDriver instance
            logger: Logger instance
            storage_handler: Storage handler for data persistence
        """
        self.driver = driver
        self.logger = logger
        self.storage = storage_handler

    def _navigate_to_slideshow(self, designer_url: str) -> bool:
        """Navigate to designer page and enter slideshow view."""
        try:
            self.driver.get(designer_url)
            time.sleep(2)  # Wait for page load

            # First try to find and click the View Slideshow button
            try:
                gallery = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CLASS_NAME, "RunwayShowPageGalleryCta-fmTQJF")
                    )
                )
                self.driver.execute_script("arguments[0].scrollIntoView(true);", gallery)
                time.sleep(1)

                button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable(
                        (
                            By.CSS_SELECTOR,
                            'a[href*="/slideshow/collection"] .button--primary span.button__label',
                        )
                    )
                )

                try:
                    button.click()
                except ElementClickInterceptedException:
                    self.driver.execute_script("arguments[0].click();", button)

            except Exception:
                # If View Slideshow button not found, try to find and click the first look thumbnail
                self.logger.info("No View Slideshow button found, trying first look thumbnail")
                first_look = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, '.GridItem-buujkM a[href*="/slideshow/collection#1"]')
                    )
                )

                try:
                    first_look.click()
                except ElementClickInterceptedException:
                    self.driver.execute_script("arguments[0].click();", first_look)

            time.sleep(2)  # Wait for slideshow to load
            return True

        except Exception as e:
            self.logger.error(f"Failed to navigate to slideshow: {str(e)}")
            return False

    def _get_total_looks(self) -> int:
        """Get the total number of looks in the slideshow."""
        try:
            look_text = (
                WebDriverWait(self.driver, 10)
                .until(
                    EC.presence_of_element_located(
                        (By.CLASS_NAME, "RunwayGalleryLookNumberText-hidXa")
                    )
                )
                .text.strip()
            )

            # Extract total from format "Look 1/25"
            total = int(look_text.split("/")[-1].strip())
            return total

        except Exception as e:
            self.logger.error(f"Error getting total looks: {str(e)}")
            return 0

    def _navigate_to_next_look(self) -> bool:
        """Navigate to the next look in the slideshow."""
        try:
            next_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[data-testid="RunwayGalleryControlNext"]')
                )
            )

            # Check if button is disabled
            if "disabled" in next_button.get_attribute("class").lower():
                return False

            # Try to click the next button
            try:
                next_button.click()
            except ElementClickInterceptedException:
                self.driver.execute_script("arguments[0].click();", next_button)

            time.sleep(1)  # Wait for next look to load
            return True

        except Exception as e:
            self.logger.error(f"Error navigating to next look: {str(e)}")
            return False