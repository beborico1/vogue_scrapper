# src/handlers/slideshow/main_scraper.py
"""Main slideshow scraper that combines all components."""

from .base_scraper import BaseSlideshowScraper
from .image_extractor import ImageExtractor
from .storage_handler import StorageHandler
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class VogueSlideshowScraper(BaseSlideshowScraper):
    """Main slideshow scraper implementation combining all components."""

    def __init__(self, driver, logger, storage_handler):
        """Initialize the main slideshow scraper.
        
        Args:
            driver: Selenium WebDriver instance
            logger: Logger instance
            storage_handler: Storage handler for data persistence
        """
        super().__init__(driver, logger, storage_handler)
        self.image_extractor = ImageExtractor(driver, logger)
        self.storage_handler = StorageHandler(storage_handler, logger)

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
                look_images = self.image_extractor.extract_look_images(current_look)
                if look_images:
                    # Store the images
                    if self.storage_handler.store_look_data(
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