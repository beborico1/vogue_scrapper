# src/handlers/images/image_extractor.py
"""Updated image extractor with optimized extraction methods."""

from typing import Dict, Optional, List
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from ...config.settings import IMAGE_RESOLUTION


class VogueImageExtractor:
    """Handles extraction and processing of image data."""

    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger

    def extract_image_data(self, img_elem) -> Optional[Dict[str, str]]:
        """Extract image data from container element."""
        try:
            img = img_elem.find_element(By.CLASS_NAME, "ResponsiveImageContainer-eybHBd")

            if not img:
                return None

            img_url = img.get_attribute("src")
            if not img_url or "/verso/static/" in img_url:
                return None

            if "assets.vogue.com" in img_url:
                # Get high resolution image URL
                img_url = img_url.replace(
                    IMAGE_RESOLUTION["original"], IMAGE_RESOLUTION["high_res"]
                )

                # Get alt text and determine type
                alt_text = img.get_attribute("alt") or ""
                img_type = self._determine_image_type(alt_text)
                
                # Get look number from parent element if available
                look_number = self._get_look_number(img_elem)

                return {
                    "url": img_url, 
                    "look_number": look_number, 
                    "alt_text": alt_text,
                    "type": img_type,
                    "timestamp": datetime.now().isoformat()
                }

            return None

        except NoSuchElementException:
            return None
        except Exception as e:
            self.logger.error(f"Error extracting image data: {str(e)}")
            return None
            
    def _determine_image_type(self, alt_text: str) -> str:
        """Determine image type based on alt text."""
        alt_lower = alt_text.lower()
        if "back" in alt_lower:
            return "back"
        elif "detail" in alt_lower:
            return "detail"
        return "front"
            
    def _get_look_number(self, img_elem) -> str:
        """Get look number from parent element or default to '0'."""
        try:
            # First try to find the look number in this element
            look_number_elem = img_elem.find_element(
                By.CLASS_NAME, "RunwayGalleryLookNumberText-hidXa"
            )
            look_text = look_number_elem.text.strip()
            return look_text.split("/")[0].replace("Look", "").strip()
        except NoSuchElementException:
            # Try to extract from URL if available
            try:
                current_url = self.driver.current_url
                if "#" in current_url:
                    return current_url.split("#")[-1]
            except:
                pass
            return "0"
            
    def extract_images_fast(self, look_number: int) -> List[Dict[str, str]]:
        """Extract all images for the current look with proper scrolling.
        
        Args:
            look_number: Current look number
            
        Returns:
            List of image data dictionaries
        """
        try:
            # Find the image collection container
            collection = self.driver.find_element(By.CLASS_NAME, "RunwayGalleryImageCollection")
            
            # Scroll to ensure all images load
            self.driver.execute_script("arguments[0].scrollIntoView(true);", collection)
            self.logger.debug(f"Scrolled to image collection for look {look_number}")
            
            # Find all image elements
            image_elements = collection.find_elements(By.CLASS_NAME, "ImageCollectionListItem-YjTJj")
            
            images = []
            for img_elem in image_elements:
                # Scroll to each image to ensure it's loaded
                self.driver.execute_script("arguments[0].scrollIntoView(true);", img_elem)
                
                image_data = self.extract_image_data(img_elem)
                if image_data:
                    # Make sure the look number is correct
                    image_data["look_number"] = str(look_number)
                    images.append(image_data)
            
            self.logger.info(f"Extracted {len(images)} images for look {look_number}")
            return images
            
        except Exception as e:
            self.logger.error(f"Error extracting images for look {look_number}: {str(e)}")
            return []

