"""Updated gallery handler with optimized image collection."""

from typing import List, Dict
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver
from logging import Logger

from ...config.settings import PAGE_LOAD_WAIT
from ...exceptions.errors import ElementNotFoundError
from .image_extractor import VogueImageExtractor


class VogueGalleryHandler:
    """Handles interaction with the image gallery interface."""

    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger
        self.image_extractor = VogueImageExtractor(driver, logger)

    def get_images_for_current_look(self) -> List[Dict[str, str]]:
        """Get all images for the current look."""
        try:
            # Wait for the gallery to be present
            gallery_wrapper = WebDriverWait(self.driver, PAGE_LOAD_WAIT).until(
                EC.presence_of_element_located((By.CLASS_NAME, "RunwayGalleryImageCollection"))
            )
            
            # Get the current look number from URL
            current_url = self.driver.current_url
            look_number = 1
            if "#" in current_url:
                try:
                    look_number = int(current_url.split("#")[-1])
                except:
                    pass
            
            # Use the faster image extraction method
            return self.image_extractor.extract_images_fast(look_number)

        except Exception as e:
            self.logger.error(f"Error getting images for current look: {str(e)}")
            return []