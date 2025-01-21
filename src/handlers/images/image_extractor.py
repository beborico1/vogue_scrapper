"""
Handles extraction and processing of image data from Vogue Runway.
Responsible for parsing image elements, extracting metadata,
and handling image resolution conversion.
"""

from typing import Dict, Optional
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from logging import Logger

from ...config.settings import IMAGE_RESOLUTION
from .look_tracker import VogueLookTracker

class VogueImageExtractor:
    """Handles extraction and processing of image data."""
    
    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger
        self.look_tracker = VogueLookTracker(driver, logger)

    def extract_image_data(self, img_elem) -> Optional[Dict[str, str]]:
        """Extract image data from container element."""
        try:
            img = img_elem.find_element(
                By.CLASS_NAME, 'ResponsiveImageContainer-eybHBd'
            )
            
            if not img:
                return None
            
            img_url = img.get_attribute('src')
            if not img_url or '/verso/static/' in img_url:
                return None
            
            if 'assets.vogue.com' in img_url:
                img_url = img_url.replace(
                    IMAGE_RESOLUTION['original'],
                    IMAGE_RESOLUTION['high_res']
                )
                
                look_number = self.look_tracker.get_look_number(img_elem)
                alt_text = img.get_attribute('alt') or ''
                
                return {
                    'url': img_url,
                    'look_number': look_number,
                    'alt_text': alt_text
                }
                
            return None
            
        except NoSuchElementException:
            return None
        except Exception as e:
            self.logger.error(f"Error extracting image data: {str(e)}")
            return None
