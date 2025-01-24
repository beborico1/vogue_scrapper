"""Enhanced slideshow navigation and image extraction for Vogue Runway scraper."""

from typing import List, Dict, Optional
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
)


class VogueSlideshowScraper:
    """Handles complete slideshow navigation and image extraction."""

    def __init__(self, driver, logger, storage_handler):
        self.driver = driver
        self.logger = logger
        self.storage = storage_handler

    def scrape_designer_slideshow(
        self, designer_url: str, season_index: int, designer_index: int
    ) -> bool:
        """
        Scrape all looks from a designer's slideshow.

        Args:
            designer_url: URL of the designer's page
            season_index: Index of the season in storage
            designer_index: Index of the designer in storage

        Returns:
            bool: True if scraping was successful
        """
        try:
            # Navigate to designer page and enter slideshow view
            if not self._navigate_to_slideshow(designer_url):
                return False

            # Get total number of looks
            total_looks = self._get_total_looks()
            if total_looks == 0:
                self.logger.error("No looks found in slideshow")
                return False

            self.logger.info(f"Starting to scrape {total_looks} looks")

            # Process each look
            current_look = 1
            while current_look <= total_looks:
                self.logger.info(f"Processing look {current_look}/{total_looks}")

                # Extract images for current look
                look_images = self._extract_look_images(current_look)
                if look_images:
                    # Store the images
                    self._store_look_data(season_index, designer_index, current_look, look_images)

                # Move to next look if not at end
                if current_look < total_looks:
                    if not self._navigate_to_next_look():
                        self.logger.error(f"Failed to navigate to next look after {current_look}")
                        break

                current_look += 1

            return True

        except Exception as e:
            self.logger.error(f"Error scraping designer slideshow: {str(e)}")
            return False

    def _navigate_to_slideshow(self, designer_url: str) -> bool:
        """Navigate to designer page and enter slideshow view."""
        try:
            self.driver.get(designer_url)
            time.sleep(2)  # Wait for page load

            # Find and scroll to gallery section
            gallery = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "RunwayShowPageGalleryCta-fmTQJF"))
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", gallery)
            time.sleep(1)

            # Find and click slideshow button
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

        except (TimeoutException, NoSuchElementException, ValueError) as e:
            self.logger.error(f"Error getting total looks: {str(e)}")
            return 0

    def _extract_look_images(self, look_number: int) -> List[Dict[str, str]]:
        """Extract all images for the current look."""
        try:
            # Find the image collection container
            collection = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "RunwayGalleryImageCollection"))
            )

            # Find all image elements
            image_elements = collection.find_elements(
                By.CLASS_NAME, "ImageCollectionListItem-YjTJj"
            )

            images = []
            for img_elem in image_elements:
                image_data = self._extract_single_image(img_elem, look_number)
                if image_data:
                    images.append(image_data)

            return images

        except Exception as e:
            self.logger.error(f"Error extracting images for look {look_number}: {str(e)}")
            return []

    def _extract_single_image(self, img_elem, look_number: int) -> Optional[Dict[str, str]]:
        """Extract data for a single image."""
        try:
            img = img_elem.find_element(By.CLASS_NAME, "ResponsiveImageContainer-eybHBd")

            if not img:
                return None

            img_url = img.get_attribute("src")
            if not img_url or "/verso/static/" in img_url:
                return None

            # Ensure we're getting the high-res version
            if "assets.vogue.com" in img_url:
                img_url = img_url.replace("w_320", "w_1920")

                return {
                    "url": img_url,
                    "look_number": str(look_number),
                    "alt_text": img.get_attribute("alt") or f"Look {look_number}",
                }

            return None

        except NoSuchElementException:
            return None

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

    def _store_look_data(
        self, season_index: int, designer_index: int, look_number: int, images: List[Dict[str, str]]
    ) -> None:
        """Store the extracted look data."""
        try:
            self.storage.update_look_data(
                season_index=season_index,
                designer_index=designer_index,
                look_number=look_number,
                images=images,
            )
        except Exception as e:
            self.logger.error(f"Error storing look {look_number} data: {str(e)}")
