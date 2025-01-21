"""
Manages tracking and counting of looks in a Vogue Runway show.
Handles look number extraction, total look counting, and 
maintains the state of current look position.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from logging import Logger

from ...config.settings import PAGE_LOAD_WAIT

class VogueLookTracker:
    """Handles tracking and counting of looks in a show."""
    
    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger

    def get_total_looks(self) -> int:
        """Get total number of looks in the show."""
        try:
            look_text = WebDriverWait(self.driver, PAGE_LOAD_WAIT).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, 'RunwayGalleryLookNumberText-hidXa')
                )
            ).text.strip()
            
            total = int(look_text.split('/')[-1].strip())
            self.logger.debug(f"Found total looks: {total}")
            return total
            
        except (NoSuchElementException, TimeoutException, ValueError) as e:
            self.logger.error(f"Error getting total looks: {str(e)}")
            return 0

    def get_look_number(self, img_elem) -> str:
        """Extract look number from image container."""
        try:
            look_number_elem = img_elem.find_element(
                By.CLASS_NAME, 'RunwayGalleryLookNumberText-hidXa'
            )
            look_text = look_number_elem.text.strip()
            return look_text.split('/')[0].replace('Look', '').strip()
        except NoSuchElementException:
            return 'Unknown'

