"""
Manages interaction with the Vogue Runway gallery interface.
Handles finding and processing image collections, coordinating
with ImageExtractor for data extraction.
"""

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
            gallery_wrapper = WebDriverWait(self.driver, PAGE_LOAD_WAIT).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, 'RunwayGalleryImageCollection')
                )
            )
            
            image_elements = gallery_wrapper.find_elements(
                By.CLASS_NAME, 'ImageCollectionListItem-YjTJj'
            )
            
            if not image_elements:
                raise ElementNotFoundError("No image elements found for current look")
            
            images = []
            for img_elem in image_elements:
                image_data = self.image_extractor.extract_image_data(img_elem)
                if image_data:
                    images.append(image_data)
            
            return images
            
        except Exception as e:
            self.logger.error(f"Error getting images for current look: {str(e)}")
            return []

