"""Seasons handling for Vogue Runway scraper."""

import time
from typing import List, Dict
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from ..config.settings import PAGE_LOAD_WAIT, SELECTORS
from ..exceptions.errors import ElementNotFoundError


class VogueSeasonsHandler:
    """Handles season-related operations for Vogue Runway."""

    def __init__(self, driver, logger, base_url: str):
        """Initialize the seasons handler."""
        self.driver = driver
        self.logger = logger
        self.base_url = base_url

    def get_seasons_list(self) -> List[Dict[str, str]]:
        """Get list of all fashion show seasons."""
        self.logger.info("Fetching seasons list...")

        try:
            url = f"{self.base_url}/fashion-shows/seasons"
            self.driver.get(url)
            time.sleep(PAGE_LOAD_WAIT)

            nav_groups = self._get_navigation_groups()
            seasons = self._process_navigation_groups(nav_groups)

            if not seasons:
                raise ElementNotFoundError("No seasons found")

            self.logger.info(f"Total valid seasons found: {len(seasons)}")
            return seasons

        except Exception as e:
            self.logger.error(f"Error getting seasons list: {str(e)}")
            raise

    def _get_navigation_groups(self) -> List:
        """Get navigation group elements."""
        nav_groups = self.driver.find_elements(By.CLASS_NAME, SELECTORS["navigation_wrapper"])

        if not nav_groups:
            raise ElementNotFoundError("No season navigation groups found")

        return nav_groups

    def _process_navigation_groups(self, nav_groups) -> List[Dict[str, str]]:
        """Process navigation groups to extract season data."""
        seasons = []
        for nav in nav_groups:
            try:
                # Skip navigation groups without year headers
                try:
                    year = self._get_year(nav)
                except NoSuchElementException:
                    continue

                # Skip non-numeric years
                if not year.isdigit():
                    continue

                seasons.extend(self._get_seasons_for_year(nav, year))
            except Exception as e:
                self.logger.warning(f"Error processing season group: {str(e)}")
                continue
        return seasons

    def _get_year(self, nav_group) -> str:
        """Extract year from navigation group."""
        year_elem = nav_group.find_element(By.CLASS_NAME, SELECTORS["navigation_heading"])
        return year_elem.text.strip()

    def _get_seasons_for_year(self, nav_group, year: str) -> List[Dict[str, str]]:
        """Extract seasons for a specific year."""
        seasons = []
        links = nav_group.find_elements(By.CLASS_NAME, SELECTORS["navigation_link"])

        for link in links:
            url = link.get_attribute("href")

            # Only include URLs that start with the fashion shows path
            if not url.startswith(f"{self.base_url}/fashion-shows/"):
                continue

            season_data = {"year": year, "season": link.text.strip(), "url": url}
            seasons.append(season_data)
            self.logger.info(f"Found season: {season_data['season']} {season_data['year']}")

        return seasons
