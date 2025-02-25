"""Enhanced slideshow scraper with progress tracking."""

import json
from typing import List, Dict, Optional
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
)


class VogueSlideshowScraper:
    def __init__(self, driver, logger, storage_handler):
        self.driver = driver
        self.logger = logger
        self.storage = storage_handler

    def scrape_designer_slideshow(
        self, designer_url: str, season_index: int, designer_index: int, progress_tracker
    ) -> bool:
        """Scrape all looks from a designer's slideshow."""
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

            # Update total looks in storage
            current_data = self.storage.read_data()
            season = current_data["seasons"][season_index]
            designer = season["designers"][designer_index]
            designer["total_looks"] = total_looks
            self.storage.write_data(current_data)

            # Initialize progress
            progress_tracker.update_progress()

            # Process each look
            current_look = 1
            while current_look <= total_looks:
                self.logger.info(f"Processing look {current_look}/{total_looks}")

                # Extract images for current look
                look_images = self._extract_look_images(current_look)
                if look_images:
                    # Store the images
                    if self._store_look_data(
                        season_index, designer_index, current_look, look_images
                    ):
                        # Update progress after each successful look
                        progress_tracker.update_look_progress(season_index, designer_index)

                        # Log progress summary every 5 looks
                        if current_look % 5 == 0:
                            self.logger.info(f"Processing progress: {current_look}/{total_looks} looks")

                # Move to next look if not at end
                if current_look < total_looks:
                    if not self._navigate_to_next_look():
                        self.logger.error(f"Failed to navigate to next look after {current_look}")
                        break

                current_look += 1

            # Final progress update
            progress_tracker.update_progress(force_save=True)
            # Log final progress
            self.logger.info(f"Completed all {total_looks} looks for this designer")
            return True

        except Exception as e:
            self.logger.error(f"Error scraping designer slideshow: {str(e)}")
            return False

    def _store_look_data(
        self, season_index: int, designer_index: int, look_number: int, images: List[Dict[str, str]]
    ) -> bool:
        """Store the extracted look data and mark as completed."""
        try:
            # Ensure we have valid images to store
            if not images:
                self.logger.warning(f"No images found for look {look_number}")
                return False
                
            # Log what we're trying to store for debugging
            self.logger.info(f"Storing {len(images)} images for look {look_number} (season: {season_index}, designer: {designer_index})")
            
            # Get current file path
            json_file_path = self.storage.get_current_file()
            if not json_file_path or not json_file_path.exists():
                self.logger.error("No valid JSON file to update")
                return False
                
            # Extract image URLs for emergency script
            img_urls = [img.get("url") for img in images if img.get("url")]
            
            if not img_urls:
                self.logger.error("No valid image URLs found")
                return False
            
            # Use external script for absolute reliability
            import subprocess
            cmd = [
                "python", 
                "/Users/beborico/dev/voguescrapper/src/look_updater.py",
                str(json_file_path),
                str(season_index),
                str(designer_index),
                str(look_number)
            ]
            
            # Add all image URLs to the command
            cmd.extend(img_urls)
            
            # Execute the update script as a separate process
            self.logger.info(f"Executing look updater script with {len(img_urls)} URLs")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"Look updater script success: {result.stdout}")
                
                # Make sure Redis storage is explicitly told to reimport from the temp file
                # This direct call is necessary to ensure proper synchronization
                if hasattr(self.storage, 'update_look_data'):
                    self.logger.info("Explicitly updating look data in Redis storage")
                    self.storage.update_look_data(
                        season_index=season_index,
                        designer_index=designer_index,
                        look_number=look_number,
                        images=images
                    )
                
                return True
            else:
                self.logger.error(f"Look updater script failed: {result.stderr}")
                
                # Try the storage API as fallback
                self.logger.warning("Falling back to storage API")
                return self.storage.update_look_data(
                    season_index=season_index,
                    designer_index=designer_index,
                    look_number=look_number,
                    images=images
                )

        except Exception as e:
            self.logger.error(f"Error storing look {look_number} data: {str(e)}")
            
            # One more try with the original storage method
            try:
                return self.storage.update_look_data(
                    season_index=season_index,
                    designer_index=designer_index,
                    look_number=look_number,
                    images=images
                )
            except Exception as fallback_error:
                self.logger.error(f"Fallback storage also failed: {str(fallback_error)}")
                return False

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

            except (TimeoutException, NoSuchElementException):
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
                
                alt_text = img.get_attribute("alt") or f"Look {look_number}"
                
                # Determine image type based on alt text
                img_type = "front"  # Default type
                alt_lower = alt_text.lower()
                if "back" in alt_lower:
                    img_type = "back"
                elif "detail" in alt_lower:
                    img_type = "detail"
                
                # Include all required fields for the look storage
                return {
                    "url": img_url,
                    "look_number": str(look_number),
                    "alt_text": alt_text,
                    "type": img_type,
                    "timestamp": datetime.now().isoformat()
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

