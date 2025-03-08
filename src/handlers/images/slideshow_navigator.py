# src/handlers/images/slideshow_navigator.py
"""Updated slideshow navigator with optimized navigation methods."""

from typing import Dict, Any, List
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
    StaleElementReferenceException
)

from ...config.settings import PAGE_LOAD_WAIT
from ...utils.wait_utils import (
    wait_for_page_load, 
    wait_for_element_presence, 
    wait_for_element_clickable,
    wait_for_url_change,
    wait_for_staleness
)


class VogueSlideshowNavigator:
    """Handles navigation through the slideshow interface with optimizations."""

    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger

    def is_slideshow_button_present(self) -> bool:
        """Check if the 'View Slideshow' button is present."""
        try:
            # Wait for gallery container
            gallery = wait_for_element_presence(
                self.driver, 
                (By.CLASS_NAME, "RunwayShowPageGalleryCta-fmTQJF"),
                PAGE_LOAD_WAIT
            )
            
            if not gallery:
                return False
                
            # Scroll to gallery
            self.driver.execute_script("arguments[0].scrollIntoView(true);", gallery)
            
            # Wait for the button to be visible after scrolling
            button = wait_for_element_presence(
                self.driver, 
                (By.CSS_SELECTOR, 'a[href*="/slideshow/collection"] .button--primary span.button__label'),
                3
            )
            
            return button is not None
            
        except (NoSuchElementException, TimeoutException) as e:
            self.logger.debug(f"Slideshow button not found: {str(e)}")
            return False

    def navigate_to_slideshow(self) -> bool:
        """Navigate to the slideshow view."""
        try:
            # Record the initial URL to verify navigation
            initial_url = self.driver.current_url
            
            # First try to find the View Slideshow button
            try:
                gallery = wait_for_element_presence(
                    self.driver, 
                    (By.CLASS_NAME, "RunwayShowPageGalleryCta-fmTQJF"),
                    PAGE_LOAD_WAIT
                )

                if gallery:
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", gallery)
                    
                    # Wait for button to be visible and clickable
                    button = wait_for_element_clickable(
                        self.driver,
                        (By.CSS_SELECTOR, 'a[href*="/slideshow/collection"] .button--primary span.button__label'),
                        PAGE_LOAD_WAIT
                    )
    
                    if button:
                        try:
                            button.click()
                        except ElementClickInterceptedException:
                            self.logger.warning("Direct click failed, trying JavaScript click")
                            self.driver.execute_script("arguments[0].click();", button)

            except (TimeoutException, NoSuchElementException):
                # If View Slideshow button not found, try to find and click the first look thumbnail
                self.logger.info("No View Slideshow button found, trying first look thumbnail")
                first_look = wait_for_element_clickable(
                    self.driver,
                    (By.CSS_SELECTOR, '.GridItem-buujkM a[href*="/slideshow/collection#1"]'),
                    PAGE_LOAD_WAIT
                )

                if first_look:
                    try:
                        first_look.click()
                    except ElementClickInterceptedException:
                        self.logger.warning("Direct click failed, trying JavaScript click")
                        self.driver.execute_script("arguments[0].click();", first_look)
                else:
                    self.logger.error("Could not find slideshow button or first look thumbnail")
                    return False

            # Wait for URL to change, indicating successful navigation
            url_changed = wait_for_url_change(self.driver, initial_url, PAGE_LOAD_WAIT)
            if not url_changed:
                self.logger.error("URL did not change after clicking slideshow button")
                return False
            
            # Wait for page to be fully loaded
            wait_for_page_load(self.driver, PAGE_LOAD_WAIT)
            
            # Wait for slideshow gallery to be present
            gallery_present = wait_for_element_presence(
                self.driver, 
                (By.CLASS_NAME, "RunwayGalleryImageCollection"),
                PAGE_LOAD_WAIT
            ) is not None
            
            if not gallery_present:
                self.logger.error("Slideshow gallery not found after navigation")
                return False
                
            self.logger.info(f"Navigated to slideshow URL: {self.driver.current_url}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to navigate to slideshow: {str(e)}")
            return False
            
    def extract_all_look_urls(self, total_looks: int) -> Dict[int, str]:
        """Extract all look URLs efficiently without navigating to each.
        
        Args:
            total_looks: Total number of looks expected
            
        Returns:
            Dict mapping look numbers to their URLs
        """
        look_urls = {}
        self.logger.info("Attempting to extract all look URLs at once")
        
        try:
            # First try to extract from pagination navigation
            try:
                nav_container = wait_for_element_presence(
                    self.driver, 
                    (By.CLASS_NAME, "RunwayGalleryPagination-gUzrXE"),
                    PAGE_LOAD_WAIT
                )
                
                if nav_container:
                    # Get all links in the pagination
                    links = nav_container.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        href = link.get_attribute("href")
                        if href and "#" in href:
                            look_number = self._get_look_number_from_url(href)
                            if look_number:
                                look_urls[look_number] = href
                    
                    # If we found a significant number of look URLs, assume we found them all
                    if len(look_urls) >= min(10, total_looks):
                        self.logger.info(f"Found {len(look_urls)} look URLs from navigation")
                        return look_urls
            except (TimeoutException, NoSuchElementException) as e:
                self.logger.debug(f"Could not extract from pagination: {str(e)}")
            
            # Fall back to scanning the current page base URL and constructing URLs
            current_url = self.driver.current_url
            base_url = current_url.split("#")[0]
            
            # Create URLs for all looks
            for i in range(1, total_looks + 1):
                look_urls[i] = f"{base_url}#{i}"
            
            self.logger.info(f"Created {len(look_urls)} look URLs from base URL")
            return look_urls
            
        except Exception as e:
            self.logger.error(f"Error extracting look URLs: {str(e)}")
            # Fall back to an empty dict and let the caller handle it
            return {}
            
    def _get_look_number_from_url(self, url: str) -> int:
        """Extract look number from URL fragment."""
        try:
            if "#" in url:
                look_number = int(url.split("#")[-1])
                return look_number
            return 0
        except:
            return 0

    def click_next(self) -> bool:
        """Navigate to next look."""
        try:
            # Wait for the next button to be present
            next_button = wait_for_element_presence(
                self.driver,
                (By.CSS_SELECTOR, '[data-testid="RunwayGalleryControlNext"]'),
                PAGE_LOAD_WAIT
            )

            if not next_button:
                self.logger.error("Next button not found")
                return False

            # Check if the button is disabled
            if "disabled" in next_button.get_attribute("class").lower():
                self.logger.warning("Next button is disabled")
                return False

            # Record current URL to verify navigation
            current_url = self.driver.current_url
            current_fragment = current_url.split("#")[-1] if "#" in current_url else ""

            try:
                next_button.click()
            except ElementClickInterceptedException:
                self.logger.warning("Direct click failed, trying JavaScript click")
                self.driver.execute_script("arguments[0].click();", next_button)

            # Wait for URL fragment to change (indicating navigation to next look)
            try:
                WebDriverWait(self.driver, 3).until(
                    lambda d: ("#" in d.current_url and 
                             d.current_url.split("#")[-1] != current_fragment)
                )
            except TimeoutException:
                # Fragment might not have changed if the URL structure is different
                # Instead, wait for content to change
                pass
                
            # Wait for image to load after navigation
            try:
                wait_for_staleness(self.driver, next_button, 2)
            except (TimeoutException, StaleElementReferenceException):
                # Button might not be stale if the page structure remains similar
                pass
                
            # Final check - wait for gallery to be ready
            gallery = wait_for_element_presence(
                self.driver,
                (By.CLASS_NAME, "RunwayGalleryImageCollection"),
                2
            )
            
            if not gallery:
                self.logger.warning("Gallery element not found after clicking next")
                
            return True

        except Exception as e:
            self.logger.error(f"Error clicking next button: {str(e)}")
            return False