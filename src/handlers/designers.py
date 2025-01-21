"""Designers handling for Vogue Runway scraper."""

import time
from typing import List, Dict
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from ..config.settings import PAGE_LOAD_WAIT, SELECTORS
from ..exceptions.errors import ElementNotFoundError

class VogueDesignersHandler:
    """Handles designer-related operations for Vogue Runway."""
    
    def __init__(self, driver, logger):
        """Initialize the designers handler."""
        self.driver = driver
        self.logger = logger

    def get_designers_for_season(self, season_url: str) -> List[Dict[str, str]]:
        """Get list of designers for a specific season."""
        self.logger.info(f"Fetching designers for season: {season_url}")
        
        try:
            self.driver.get(season_url)
            time.sleep(PAGE_LOAD_WAIT)
            
            designer_items = self._get_designer_items()
            designers = self._process_designer_items(designer_items)
            
            if not designers:
                raise ElementNotFoundError("No designers found")
                
            self.logger.info(f"Total designers found: {len(designers)}")
            return designers
            
        except Exception as e:
            self.logger.error(f"Error getting designers: {str(e)}")
            raise

    def _get_designer_items(self) -> List:
        """Get designer item elements."""
        designer_items = self.driver.find_elements(
            By.CLASS_NAME, SELECTORS['designer_item']
        )
        
        if not designer_items:
            raise ElementNotFoundError("No designer items found")
            
        return designer_items

    def _process_designer_items(self, designer_items) -> List[Dict[str, str]]:
        """Process designer items to extract designer data."""
        designers = []
        for item in designer_items:
            try:
                designer_data = self._extract_designer_data(item)
                if designer_data:
                    designers.append(designer_data)
            except NoSuchElementException as e:
                self.logger.warning(f"Error processing designer item: {str(e)}")
                continue
        return designers

    def _extract_designer_data(self, item) -> Dict[str, str]:
        """Extract designer data from item element."""
        link = item.find_element(
            By.CLASS_NAME, SELECTORS['designer_link']
        )
        designer_data = {
            'name': link.text.strip(),
            'url': link.get_attribute('href')
        }
        self.logger.info(f"Found designer: {designer_data['name']}")
        return designer_data