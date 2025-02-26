# src/handlers/slideshow/image_extractor.py
"""Image extraction functionality for slideshow scraper."""

from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from typing import Dict, Optional, List
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class ImageExtractor:
    """Handles extraction of image data from slideshow."""

    def __init__(self, driver, logger):
        """Initialize the image extractor.
        
        Args:
            driver: Selenium WebDriver instance
            logger: Logger instance
        """
        self.driver = driver
        self.logger = logger

    def extract_look_images(self, look_number: int) -> List[Dict[str, str]]:
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
        except Exception as e:
            self.logger.error(f"Error extracting single image: {str(e)}")
            return None