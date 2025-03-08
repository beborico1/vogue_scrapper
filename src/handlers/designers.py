# handlers/designers.py
"""Designers handling for Vogue Runway scraper."""

from typing import List, Dict
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

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
            # Validate that this is a valid runway season URL before proceeding
            if "/article/" in season_url or not any(pattern in season_url for pattern in ["-ready-to-wear", "-menswear", "-couture", "-bridal", "-resort"]):
                self.logger.warning(f"Invalid season URL (likely an article): {season_url}")
                return []
                
            self.driver.get(season_url)
            
            # Wait for page to fully load
            WebDriverWait(self.driver, timeout=PAGE_LOAD_WAIT).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            
            # Use the navigation links to find designers rather than summary items
            # This targets specifically the designer navigation links within the season page
            designers = self._get_designers_from_navigation()
            
            if not designers:
                self.logger.warning(f"No designers found using navigation. Fallback to summary items.")
                # Fallback to the old method only for valid runway URLs
                designer_items = self._get_designer_items()
                designers = self._process_designer_items(designer_items)

            if not designers:
                raise ElementNotFoundError("No designers found")

            # Filter out any designer URLs that contain "/article/"
            designers = [d for d in designers if "/article/" not in d["url"]]
            
            self.logger.info(f"Total valid designers found: {len(designers)}")
            return designers

        except Exception as e:
            self.logger.error(f"Error getting designers: {str(e)}")
            raise
            
    def _get_designers_from_navigation(self) -> List[Dict[str, str]]:
        """Get designers from the navigation links on the season page."""
        designers = []
        try:
            # Wait for the navigation to load
            WebDriverWait(self.driver, timeout=PAGE_LOAD_WAIT).until(
                EC.presence_of_element_located((By.CLASS_NAME, SELECTORS["navigation_link"]))
            )
            
            # Look for navigation links with designer names
            nav_links = self.driver.find_elements(By.CLASS_NAME, SELECTORS["navigation_link"])
            
            for link in nav_links:
                try:
                    url = link.get_attribute("href")
                    # Only include runway designer URLs
                    if url and "/fashion-shows/" in url and "/article/" not in url:
                        name = link.text.strip()
                        # Skip "See More" type links and empty names
                        if name and not any(word in name.upper() for word in ["MORE", "SEE ALL", "VIEW"]):
                            designer_data = {"name": name, "url": url}
                            designers.append(designer_data)
                            self.logger.info(f"Found designer from navigation: {name}")
                except Exception as e:
                    self.logger.debug(f"Error processing nav link: {str(e)}")
                    continue
                    
            return designers
        except (TimeoutException, NoSuchElementException) as e:
            self.logger.warning(f"Error getting designers from navigation: {str(e)}")
            return []

    def _get_designer_items(self) -> List:
        """Get designer item elements from summary items (fallback method)."""
        try:
            # Wait for designer items to load with a specific timeout
            WebDriverWait(self.driver, timeout=PAGE_LOAD_WAIT).until(
                EC.presence_of_element_located((By.CLASS_NAME, SELECTORS["designer_item"]))
            )
            
            designer_items = self.driver.find_elements(By.CLASS_NAME, SELECTORS["designer_item"])

            if not designer_items:
                self.logger.warning("No designer items found in summary")
                return []

            return designer_items
            
        except (TimeoutException, NoSuchElementException) as e:
            self.logger.warning(f"Error finding designer items: {str(e)}")
            return []

    def _process_designer_items(self, designer_items) -> List[Dict[str, str]]:
        """Process designer items to extract designer data."""
        designers = []
        for item in designer_items:
            try:
                designer_data = self._extract_designer_data(item)
                if designer_data and "/article/" not in designer_data["url"]:
                    designers.append(designer_data)
            except NoSuchElementException as e:
                self.logger.warning(f"Error processing designer item: {str(e)}")
                continue
        return designers

    def _extract_designer_data(self, item) -> Dict[str, str]:
        """Extract designer data from item element."""
        try:
            link = item.find_element(By.CLASS_NAME, SELECTORS["designer_link"])
            name = link.text.strip()
            url = link.get_attribute("href")
            
            # Filter out articles and non-designer content
            if not name or "/article/" in url or any(word in name.upper() for word in ["MORE FROM", "SEE MORE"]):
                return None
                
            designer_data = {"name": name, "url": url}
            self.logger.info(f"Found designer: {name}")
            return designer_data
        except Exception as e:
            self.logger.debug(f"Error extracting designer data: {str(e)}")
            return None