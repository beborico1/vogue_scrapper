# handlers/images/slideshow_navigator.py
"""
Handles navigation through the Vogue Runway slideshow interface.
Responsible for finding and interacting with slideshow controls,
managing page transitions, and handling navigation-related errors.
"""

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

from ...config.settings import PAGE_LOAD_WAIT
from ...exceptions.errors import ElementNotFoundError


class VogueSlideshowNavigator:
    """Handles navigation through the slideshow interface."""

    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger

    def is_slideshow_button_present(self) -> bool:
        """Check if the 'View Slideshow' button is present."""
        try:
            gallery = WebDriverWait(self.driver, PAGE_LOAD_WAIT).until(
                EC.presence_of_element_located((By.CLASS_NAME, "RunwayShowPageGalleryCta-fmTQJF"))
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", gallery)
            time.sleep(2)

            button = gallery.find_element(
                By.CSS_SELECTOR,
                'a[href*="/slideshow/collection"] .button--primary span.button__label',
            )
            return True
        except (NoSuchElementException, TimeoutException) as e:
            self.logger.debug(f"Slideshow button not found: {str(e)}")
            return False

    def navigate_to_slideshow(self) -> bool:
        """Navigate to the slideshow view."""
        try:
            # First try to find the View Slideshow button
            try:
                gallery = WebDriverWait(self.driver, PAGE_LOAD_WAIT).until(
                    EC.presence_of_element_located(
                        (By.CLASS_NAME, "RunwayShowPageGalleryCta-fmTQJF")
                    )
                )

                self.driver.execute_script("arguments[0].scrollIntoView(true);", gallery)
                time.sleep(2)

                button = WebDriverWait(self.driver, PAGE_LOAD_WAIT).until(
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
                    self.logger.warning("Direct click failed, trying JavaScript click")
                    self.driver.execute_script("arguments[0].click();", button)

            except (TimeoutException, NoSuchElementException):
                # If View Slideshow button not found, try to find and click the first look thumbnail
                self.logger.info("No View Slideshow button found, trying first look thumbnail")
                first_look = WebDriverWait(self.driver, PAGE_LOAD_WAIT).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, '.GridItem-buujkM a[href*="/slideshow/collection#1"]')
                    )
                )

                try:
                    first_look.click()
                except ElementClickInterceptedException:
                    self.logger.warning("Direct click failed, trying JavaScript click")
                    self.driver.execute_script("arguments[0].click();", first_look)

            time.sleep(PAGE_LOAD_WAIT)
            self.logger.info(f"Navigated to slideshow URL: {self.driver.current_url}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to navigate to slideshow: {str(e)}")
            return False

    def click_next(self) -> bool:
        """Navigate to next look."""
        try:
            next_button = WebDriverWait(self.driver, PAGE_LOAD_WAIT).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[data-testid="RunwayGalleryControlNext"]')
                )
            )

            if "disabled" in next_button.get_attribute("class").lower():
                self.logger.warning("Next button is disabled")
                return False

            try:
                next_button.click()
            except ElementClickInterceptedException:
                self.logger.warning("Direct click failed, trying JavaScript click")
                self.driver.execute_script("arguments[0].click();", next_button)

            time.sleep(1)
            return True

        except Exception as e:
            self.logger.error(f"Error clicking next button: {str(e)}")
            return False
