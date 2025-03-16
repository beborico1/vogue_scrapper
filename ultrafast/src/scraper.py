"""
Ultrafast Vogue Scraper - Main scraper class

This is the main implementation of the ultrafast scraper that:
1. Authenticates with Vogue
2. Extracts all season and collection URLs
3. Processes each collection page with all sections (Collection, Details, Beauty, etc.)
4. Stores everything in Redis for high performance
"""

import os
import sys
import time
import logging
from typing import List, Dict, Any, Tuple, Optional
import concurrent.futures
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

from .config.settings import Config
from .utils.driver import setup_chrome_driver
from .utils.storage import RedisStorage
from .utils.auth_cookies import apply_auth_cookies
from .handlers.auth import AuthHandler


class UltrafastVogueScraper:
    """
    Ultrafast implementation of the Vogue Scraper.
    
    Features:
    - Non-headless browser for visual monitoring
    - Direct extraction from collection pages with all sections
    - Handling of "Load More" buttons
    - Redis storage for high performance
    """
    
    def __init__(
        self, 
        config: Config, 
        logger=None, 
        resume: bool = False,
        use_static_seasons: bool = False,
        sequential: bool = False
    ):
        """
        Initialize the Ultrafast Vogue Scraper.
        
        Args:
            config: Configuration object
            logger: Logger instance (optional)
            resume: Whether to resume from previously stored data
            use_static_seasons: Whether to use statically generated seasons
            sequential: Whether to process collections sequentially (no parallel)
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.resume = resume
        self.use_static_seasons = use_static_seasons
        self.sequential = sequential
        self.driver = None
        
        # Initialize Redis storage
        self.storage = RedisStorage(
            host=config.redis.HOST,
            port=config.redis.PORT,
            db=config.redis.DB,
            password=config.redis.PASSWORD,
            prefix=config.redis.KEY_PREFIX
        )
        
        # Create data directory if it doesn't exist
        os.makedirs(f"{config.data_dir}", exist_ok=True)
    
    def run(self):
        """
        Run the ultrafast scraping process.
        
        This is the main entry point that orchestrates the entire scraping workflow.
        """
        self.logger.info("=== Starting Ultrafast Vogue Scraper ===")
        
        try:
            # Initialize Chrome driver (non-headless)
            self.driver = setup_chrome_driver(self.config)
            
            # Authenticate with Vogue
            auth_handler = AuthHandler(self.driver, self.config, self.logger)
            if not auth_handler.authenticate():
                self.logger.error("Authentication failed")
                return
            
            self.logger.info("Authentication successful")
            
            # Get seasons if not resuming
            if not self.resume:
                if self.use_static_seasons:
                    # Use statically generated seasons
                    seasons = self._load_static_seasons()
                    if not seasons:
                        self.logger.error("No static seasons found")
                        return
                    
                    self.logger.info(f"Using {len(seasons)} statically generated seasons")
                else:
                    # Get all seasons dynamically
                    seasons = self.get_seasons()
                    if not seasons:
                        self.logger.error("No seasons found")
                        return
                    
                    self.logger.info(f"Found {len(seasons)} seasons dynamically")
                
                # Store seasons
                self.storage.store_seasons(seasons)
                
                # Write seasons to text file (if not using static seasons file)
                if not self.use_static_seasons:
                    self.write_urls_to_file(
                        [season['url'] for season in seasons],
                        f"{self.config.data_dir}/seasons.txt"
                    )
            else:
                # Load seasons from storage
                seasons = self.storage.get_seasons()
                self.logger.info(f"Resumed with {len(seasons)} seasons from storage")
            
            # Process all seasons
            self.process_all_seasons(seasons)
            
        except Exception as e:
            self.logger.error(f"Error in scraper: {str(e)}")
        finally:
            # Clean up
            if self.driver:
                self.driver.quit()
    
    def get_seasons(self) -> List[Dict[str, str]]:
        """
        Get all fashion show seasons from Vogue.
        
        Returns:
            List of season dictionaries with season, year, and URL
        """
        self.logger.info(f"Getting seasons from {self.config.FASHION_SHOWS_URL}/seasons")
        
        try:
            # Navigate to the fashion shows seasons page directly
            self.driver.get(f"{self.config.FASHION_SHOWS_URL}/seasons")
            
            # Wait for the page to load
            time.sleep(self.config.timing.PAGE_LOAD_WAIT)
            
            # Find all season links
            season_links = self.driver.find_elements(By.TAG_NAME, "a")
            seasons = []
            
            for link in season_links:
                try:
                    # Get URL and text
                    url = link.get_attribute("href")
                    text = link.text.strip()
                    
                    # Filter for valid season links
                    if (url and text and 
                        "/fashion-shows/" in url and 
                        not "/seasons" in url and 
                        not "/designers" in url and
                        not "/featured" in url):
                        
                        # Check if it contains keywords that indicate it's a season
                        season_keywords = ["SPRING", "FALL", "RESORT", "COUTURE", "READY-TO-WEAR", "MENSWEAR"]
                        if any(keyword in text.upper() for keyword in season_keywords):
                            # Parse season and year
                            parts = text.split()
                            if len(parts) >= 2:
                                season = " ".join(parts[:-1])
                                year = parts[-1]
                                
                                # Add to seasons list if not already present
                                season_data = {
                                    "season": season,
                                    "year": year,
                                    "url": url
                                }
                                
                                if season_data not in seasons:
                                    seasons.append(season_data)
                                    self.logger.info(f"Found season: {season} {year}")
                except Exception as e:
                    self.logger.warning(f"Error processing season link: {str(e)}")
            
            # If we didn't find any seasons on the seasons page, try getting them from the latest shows page
            if not seasons:
                self.logger.info("No seasons found on seasons page, trying latest shows...")
                return self._get_seasons_from_latest_shows()
            
            return seasons
            
        except Exception as e:
            self.logger.error(f"Error getting seasons: {str(e)}")
            return self._get_seasons_from_latest_shows()  # Fallback method
    
    def _get_seasons_from_latest_shows(self) -> List[Dict[str, str]]:
        """
        Alternative method to get seasons from the latest shows page.
        
        Returns:
            List of season dictionaries
        """
        self.logger.info(f"Getting seasons from {self.config.FASHION_SHOWS_URL}/latest-shows")
        
        try:
            # Navigate to latest shows page
            self.driver.get(f"{self.config.FASHION_SHOWS_URL}/latest-shows")
            
            # Wait for the page to load
            time.sleep(self.config.timing.PAGE_LOAD_WAIT)
            
            # Get all collection links on the page
            collection_links = self.driver.find_elements(
                By.XPATH, 
                "//a[contains(@href, '/fashion-shows/') and not(contains(@href, '/latest-shows'))]"
            )
            
            # Extract unique season URLs from collection URLs
            season_urls = set()
            for link in collection_links:
                try:
                    url = link.get_attribute("href")
                    if url and "/fashion-shows/" in url:
                        # Extract season URL pattern (e.g., /fashion-shows/fall-2024-ready-to-wear)
                        parts = url.split("/")
                        if len(parts) >= 5:
                            season_url = "/".join(parts[:5])
                            season_urls.add(season_url)
                except Exception as e:
                    self.logger.warning(f"Error extracting season URL: {str(e)}")
            
            # Create season dictionaries
            seasons = []
            for url in season_urls:
                try:
                    # Extract season and year from URL
                    parts = url.split("/")
                    if len(parts) >= 5:
                        season_part = parts[4]
                        season_parts = season_part.split("-")
                        
                        if len(season_parts) >= 3:
                            season_name = season_parts[0].capitalize()
                            year = season_parts[1]
                            category = " ".join(p.capitalize() for p in season_parts[2:])
                            
                            full_season = f"{season_name} {category}"
                            
                            seasons.append({
                                "season": full_season,
                                "year": year,
                                "url": url
                            })
                            self.logger.info(f"Found season from URL: {full_season} {year}")
                except Exception as e:
                    self.logger.warning(f"Error parsing season URL {url}: {str(e)}")
            
            # Hardcode a few seasons if we still couldn't find any
            if not seasons:
                self.logger.warning("No seasons found from links, using hardcoded fallback seasons")
                fallback_seasons = [
                    {
                        "season": "Fall Ready-to-Wear",
                        "year": "2025",
                        "url": "https://www.vogue.com/fashion-shows/fall-2025-ready-to-wear"
                    },
                    {
                        "season": "Spring Ready-to-Wear",
                        "year": "2025",
                        "url": "https://www.vogue.com/fashion-shows/spring-2025-ready-to-wear"
                    },
                    {
                        "season": "Fall Couture",
                        "year": "2024",
                        "url": "https://www.vogue.com/fashion-shows/fall-2024-couture"
                    }
                ]
                return fallback_seasons
            
            return seasons
            
        except Exception as e:
            self.logger.error(f"Error getting seasons from latest shows: {str(e)}")
            
            # Return hardcoded fallback seasons as last resort
            self.logger.warning("Using hardcoded fallback seasons")
            return [
                {
                    "season": "Fall Ready-to-Wear",
                    "year": "2025",
                    "url": "https://www.vogue.com/fashion-shows/fall-2025-ready-to-wear"
                },
                {
                    "season": "Spring Ready-to-Wear",
                    "year": "2025", 
                    "url": "https://www.vogue.com/fashion-shows/spring-2025-ready-to-wear"
                }
            ]
    
    def process_all_seasons(self, seasons: List[Dict[str, str]]):
        """
        Process all seasons sequentially.
        
        Args:
            seasons: List of season dictionaries
        """
        for i, season in enumerate(seasons):
            try:
                self.logger.info(f"Processing season {i+1}/{len(seasons)}: {season['season']} {season['year']}")
                self.process_season(season)
            except Exception as e:
                self.logger.error(f"Error processing season {season['season']} {season['year']}: {str(e)}")
    
    def process_season(self, season: Dict[str, str]):
        """
        Process a single season.
        
        Args:
            season: Season dictionary with season, year, and URL
        """
        try:
            # Get collections for this season
            collections = self.get_collections(season['url'])
            if not collections:
                self.logger.warning(f"No collections found for season: {season['url']}")
                return
            
            # Store collections
            self.storage.store_season_collections(season['url'], collections)
            
            # Write collections to text file
            self.write_urls_to_file(
                [collection['url'] for collection in collections],
                f"{self.config.data_dir}/collections.txt"
            )
            
            self.logger.info(f"Found {len(collections)} collections for {season['season']} {season['year']}")
            
            # Process collections in parallel or sequentially
            if self.sequential:
                self.logger.info("Processing collections sequentially")
                for i, collection in enumerate(collections):
                    try:
                        self.logger.info(f"Processing collection {i+1}/{len(collections)}: {collection['name']}")
                        self.process_collection(collection)
                    except Exception as e:
                        self.logger.error(f"Error processing collection {collection['name']}: {str(e)}")
            else:
                self.logger.info(f"Processing collections in parallel with {self.config.workers} workers")
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.workers) as executor:
                    futures = [
                        executor.submit(self.process_collection, collection)
                        for collection in collections
                    ]
                    
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            future.result()
                        except Exception as e:
                            self.logger.error(f"Error in collection processing thread: {str(e)}")
        
        except Exception as e:
            self.logger.error(f"Error processing season {season['url']}: {str(e)}")
    
    def get_collections(self, season_url: str) -> List[Dict[str, str]]:
        """
        Get all collections for a specific season.
        
        Args:
            season_url: URL of the season page
            
        Returns:
            List of collection dictionaries with name and URL
        """
        self.logger.info(f"Getting collections from {season_url}")
        
        try:
            # Check if we already have collections for this season
            existing_collections = self.storage.get_collections(season_url)
            if existing_collections:
                self.logger.info(f"Found {len(existing_collections)} collections in storage")
                return existing_collections
            
            # Navigate to the season page
            self.driver.get(season_url)
            
            # Wait for the page to load
            time.sleep(self.config.timing.PAGE_LOAD_WAIT)
            
            # Scroll the page to load all content
            self._scroll_page_to_bottom(self.driver)
            
            # Try to find all designer items (links to collections)
            collection_links = self.driver.find_elements(
                By.XPATH,
                "//a[contains(@href, '/fashion-shows/') and not(contains(@href, '/seasons')) and not(contains(@href, '/designers'))]"
            )
            
            collections = []
            
            for link in collection_links:
                try:
                    # Get designer name and URL
                    url = link.get_attribute("href")
                    name = link.text.strip()
                    
                    # Skip if missing data or if it's not a collection URL
                    if not url or not name or "/fashion-shows/" not in url:
                        continue
                        
                    # Skip if URL is the same as the season page
                    if url == season_url:
                        continue
                    
                    # Check if URL has one more path component than the season URL
                    # (e.g., season: /fashion-shows/fall-2025-ready-to-wear, 
                    #       collection: /fashion-shows/fall-2025-ready-to-wear/chanel)
                    season_parts = season_url.rstrip('/').split('/')
                    collection_parts = url.rstrip('/').split('/')
                    
                    if len(collection_parts) == len(season_parts) + 1:
                        # This is likely a valid collection URL
                        collection_data = {
                            "name": name or collection_parts[-1].replace('-', ' ').title(),
                            "url": url
                        }
                        
                        # Add if not already in the list
                        if collection_data not in collections:
                            collections.append(collection_data)
                
                except Exception as e:
                    self.logger.warning(f"Error processing collection link: {str(e)}")
            
            # Sort collections by name
            collections = sorted(collections, key=lambda x: x["name"])
            
            return collections
            
        except Exception as e:
            self.logger.error(f"Error getting collections for {season_url}: {str(e)}")
            return []
    
    def process_collection(self, collection: Dict[str, str]):
        """
        Process a single collection.
        
        Args:
            collection: Collection dictionary with name and URL
        """
        try:
            # Skip if already processed
            if self.storage.is_collection_completed(collection['url']):
                self.logger.info(f"Collection already processed: {collection['name']}")
                return
            
            # Create a new driver for this thread
            thread_driver = setup_chrome_driver(self.config)
            thread_logger = logging.getLogger(f"Collection.{collection['name'].replace(' ', '_')}")
            
            try:
                thread_logger.info(f"Processing collection: {collection['name']}")
                
                # Apply cookies for authentication
                cookie_auth_success = apply_auth_cookies(thread_driver, self.config)
                
                if cookie_auth_success:
                    thread_logger.info(f"Authentication via cookies successful for: {collection['name']}")
                else:
                    # Only do full authentication if cookie auth failed
                    thread_logger.info(f"Cookie auth failed, trying full auth for: {collection['name']}")
                    auth_handler = AuthHandler(thread_driver, self.config, thread_logger)
                    auth_success = auth_handler.authenticate()
                    
                    if not auth_success:
                        thread_logger.error(f"Failed to authenticate for collection: {collection['name']}")
                        return
                    
                    thread_logger.info(f"Full authentication successful for: {collection['name']}")
                
                # Extract looks from collection page
                sections = self.extract_collection_looks(thread_driver, collection['url'])
                
                # Store the results
                if sections:
                    self.storage.store_collection_looks(collection['url'], sections)
                    thread_logger.info(f"Completed processing collection: {collection['name']}")
                else:
                    thread_logger.warning(f"No sections found for collection: {collection['name']}")
            
            finally:
                # Clean up the thread's driver
                thread_driver.quit()
        
        except Exception as e:
            self.logger.error(f"Error processing collection {collection['url']}: {str(e)}")
    
    def extract_collection_looks(
        self,
        driver,
        collection_url: str
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        Extract all looks from a collection page.
        
        Args:
            driver: Selenium WebDriver instance
            collection_url: URL of the collection page
            
        Returns:
            Dictionary mapping section names to lists of image data
        """
        try:
            # Navigate to the collection page
            driver.get(collection_url)
            
            # Wait for the page to load
            time.sleep(self.config.timing.PAGE_LOAD_WAIT)
            
            # Scroll down to load all content
            self._scroll_page_to_bottom(driver)
            
            # Extract the coverage information (optional)
            coverage = self._extract_coverage(driver)
            if coverage:
                self.logger.info(f"Found coverage: {coverage[:100]}...")
            
            # Find and click all "Load More" buttons
            load_more_count = self._expand_all_sections(driver)
            if load_more_count < 3:
                self.logger.warning(f"Could not find three load more buttons. Only found {load_more_count}")
            
            # After expanding, scroll down once more to load all content
            self._scroll_page_to_bottom(driver)
            
            # Find all gallery sections
            sections = self._extract_gallery_sections(driver)
            
            if not sections:
                self.logger.warning(f"No gallery sections found for {collection_url}")
            else:
                self.logger.info(f"Found {len(sections)} sections with {sum(len(looks) for looks in sections.values())} total looks")
            
            return sections
            
        except Exception as e:
            self.logger.error(f"Error extracting collection looks from {collection_url}: {str(e)}")
            return {}
    
    def _scroll_page_to_bottom(self, driver):
        """
        Scroll the page to the bottom to load all content.
        
        Args:
            driver: Selenium WebDriver instance
        """
        self.logger.info("Scrolling to load all content")
        
        # Get initial scroll height
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        while True:
            # Scroll down
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Wait for new content to load
            time.sleep(self.config.timing.SCROLL_PAUSE_TIME)
            
            # Calculate new scroll height
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            # Break if no more new content
            if new_height == last_height:
                break
                
            last_height = new_height
    
    def _extract_coverage(self, driver) -> str:
        """
        Extract coverage text from the collection page.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            Coverage text, or empty string if not found
        """
        try:
            # Find coverage elements (article text)
            coverage_elements = driver.find_elements(
                By.CSS_SELECTOR, 
                "div.BaseArticle-bxLoKM, p.BaseParagraph-duKfxb, .BaseText-ewrbLt"
            )
            
            coverage_text = []
            for element in coverage_elements:
                text = element.text.strip()
                if text:
                    coverage_text.append(text)
            
            return "\n\n".join(coverage_text)
            
        except Exception as e:
            self.logger.warning(f"Error extracting coverage: {str(e)}")
            return ""
    
    def _expand_all_sections(self, driver) -> int:
        """
        Find and click all "Load More" buttons.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            Number of "Load More" buttons clicked
        """
        self.logger.info("Expanding all sections with Load More buttons")
        
        # Find all Load More buttons
        load_more_count = 0
        max_attempts = 10
        
        for attempt in range(max_attempts):
            try:
                # Find all buttons with the "Load More" text
                buttons = driver.find_elements(
                    By.XPATH, 
                    "//button[contains(@class, 'Button') and (.//span[contains(text(), 'Load More')] or .//span[contains(text(), 'load more')])]"
                )
                
                if not buttons:
                    self.logger.info(f"No more Load More buttons found after {load_more_count} clicks")
                    break
                
                # Click each button
                for button in buttons:
                    try:
                        if button.is_displayed():
                            # Scroll to the button
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                            time.sleep(0.5)
                            
                            # Click the button
                            button.click()
                            load_more_count += 1
                            self.logger.info(f"Clicked Load More button #{load_more_count}")
                            
                            # Wait for more content to load
                            time.sleep(self.config.timing.LOAD_MORE_WAIT)
                    except (ElementClickInterceptedException, Exception) as e:
                        self.logger.warning(f"Error clicking Load More button: {str(e)}")
                
                # Break if we've clicked at least 3 buttons
                if load_more_count >= 3:
                    self.logger.info("Found and clicked at least 3 Load More buttons")
                    break
                    
            except Exception as e:
                self.logger.warning(f"Error expanding sections (attempt {attempt+1}): {str(e)}")
            
            # Wait a bit before trying again
            time.sleep(1)
        
        return load_more_count
    
    def _extract_gallery_sections(self, driver) -> Dict[str, List[Dict[str, str]]]:
        """
        Extract all gallery sections and their images.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            Dictionary mapping section names to lists of image data
        """
        try:
            # Try to find sections by class name first
            section_elements = driver.find_elements(
                By.XPATH,
                "//*[contains(@class, 'Gallery') and .//h2]"
            )
            
            # If no sections found, try to find any container with images
            if not section_elements:
                self.logger.info("No gallery sections found by class, trying to find containers with images")
                section_elements = driver.find_elements(
                    By.XPATH,
                    "//section[.//img] | //div[.//img and count(.//img) > 5]"
                )
            
            if not section_elements:
                self.logger.warning("No gallery sections found")
                return {}
            
            self.logger.info(f"Found {len(section_elements)} gallery sections")
            
            sections = {}
            
            for section_elem in section_elements:
                try:
                    # Get section title
                    try:
                        title_elem = section_elem.find_element(By.XPATH, ".//h2")
                        section_name = title_elem.text.strip()
                    except NoSuchElementException:
                        # If no title found, use a default
                        section_name = f"Section{len(sections)+1}"
                    
                    self.logger.info(f"Processing section: {section_name}")
                    
                    # Find all image elements in this section
                    img_elements = section_elem.find_elements(By.TAG_NAME, "img")
                    
                    self.logger.info(f"Found {len(img_elements)} images in section {section_name}")
                    
                    # Extract data from each image
                    section_looks = []
                    
                    for i, img in enumerate(img_elements):
                        try:
                            # Skip very small images (likely icons)
                            width = img.get_attribute("width")
                            if width and int(width) < 100:
                                continue
                                
                            look_data = self._extract_image_data(img, i+1, section_elem)
                            if look_data:
                                section_looks.append(look_data)
                        except Exception as e:
                            self.logger.warning(f"Error extracting image {i+1}: {str(e)}")
                    
                    if section_looks:
                        sections[section_name] = section_looks
                    
                except Exception as e:
                    self.logger.warning(f"Error processing section: {str(e)}")
            
            return sections
            
        except Exception as e:
            self.logger.error(f"Error extracting gallery sections: {str(e)}")
            return {}
    
    def _extract_image_data(self, img_element, default_number: int, section_elem) -> Optional[Dict[str, str]]:
        """
        Extract image data from an img element.
        
        Args:
            img_element: Image element
            default_number: Default look number if not found
            section_elem: Parent section element
            
        Returns:
            Dictionary with image data or None if extraction failed
        """
        try:
            # Get image URL
            img_url = img_element.get_attribute("src")
            if not img_url or "/verso/static/" in img_url:
                return None
            
            # Get high-resolution version
            if "assets.vogue.com" in img_url:
                img_url = img_url.replace(
                    self.config.image.RESOLUTION["original"],
                    self.config.image.RESOLUTION["high_res"]
                )
            
            # Get srcset for even higher resolution if available
            srcset = img_element.get_attribute("srcset")
            if srcset:
                # Parse srcset to get highest resolution
                parts = srcset.split(',')
                for part in reversed(parts):  # Start from the end to get highest res
                    if 'w_' in part and 'http' in part:
                        url_part = part.strip().split(' ')[0]
                        if url_part:
                            img_url = url_part
                            break
            
            # Try to get caption/look number
            try:
                # First look for figcaption
                figure_parent = self._find_parent_by_tag(img_element, "figure")
                if figure_parent:
                    caption_elem = figure_parent.find_element(By.TAG_NAME, "figcaption")
                    caption_text = caption_elem.text.strip()
                else:
                    # Look for any text nearby with "Look" in it
                    potential_captions = section_elem.find_elements(
                        By.XPATH, 
                        f".//div[contains(text(), 'Look')] | .//span[contains(text(), 'Look')]"
                    )
                    
                    if potential_captions:
                        # Find the closest one to this image
                        caption_text = potential_captions[0].text.strip()
                    else:
                        caption_text = f"Look {default_number}"
                
                # Extract look number from caption
                import re
                look_match = re.search(r"Look (\d+)", caption_text)
                if look_match:
                    look_number = look_match.group(1)
                else:
                    look_number = str(default_number)
                    
            except NoSuchElementException:
                caption_text = f"Look {default_number}"
                look_number = str(default_number)
            
            # Get alt text
            alt_text = img_element.get_attribute("alt") or caption_text
            
            # Determine image type
            img_type = "front"  # Default type
            alt_lower = alt_text.lower()
            
            if "back" in alt_lower:
                img_type = "back"
            elif "detail" in alt_lower:
                img_type = "detail"
            
            # Create result dictionary
            return {
                "url": img_url,
                "look_number": look_number,
                "alt_text": alt_text,
                "caption": caption_text,
                "type": img_type,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
            }
            
        except Exception as e:
            self.logger.warning(f"Error extracting image data: {str(e)}")
            return None
    
    def _find_parent_by_tag(self, element, tag_name):
        """
        Find parent element with a specific tag.
        
        Args:
            element: Starting element
            tag_name: Tag name to search for
            
        Returns:
            Parent element or None if not found
        """
        try:
            parent = element
            for _ in range(5):  # Limit to 5 levels up
                parent = parent.find_element(By.XPATH, "..")
                if parent.tag_name.lower() == tag_name.lower():
                    return parent
            return None
        except:
            return None
    
    def _load_static_seasons(self) -> List[Dict[str, str]]:
        """
        Load seasons from static JSON file.
        
        Returns:
            List of season dictionaries
        """
        try:
            import json
            seasons_file = f"{self.config.data_dir}/seasons.json"
            
            if not os.path.exists(seasons_file):
                self.logger.error(f"Static seasons file not found: {seasons_file}")
                self.logger.info("Generating static seasons...")
                
                # Import and run the static seasons generator
                sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from ultrafast import static_seasons
                
                # Generate and save seasons (from 1980 to get all history)
                start_year = 1980  # Starting from 1980 to cover Vogue's digital archive
                end_year = datetime.now().year + 1
                seasons = static_seasons.generate_season_urls(start_year, end_year)
                
                # Save to data directory
                static_seasons.write_seasons_to_file(seasons, os.path.join(self.config.data_dir, "seasons.txt"))
                static_seasons.write_seasons_to_json(seasons, os.path.join(self.config.data_dir, "seasons.json"))
            
            with open(seasons_file, 'r') as f:
                seasons = json.load(f)
                
            self.logger.info(f"Loaded {len(seasons)} seasons from static file")
            return seasons
            
        except Exception as e:
            self.logger.error(f"Error loading static seasons: {str(e)}")
            
            # Return hardcoded fallback as last resort
            self.logger.warning("Using hardcoded fallback seasons")
            return [
                {
                    "season": "Fall Ready-to-Wear",
                    "year": "2025",
                    "url": "https://www.vogue.com/fashion-shows/fall-2025-ready-to-wear"
                },
                {
                    "season": "Spring Ready-to-Wear",
                    "year": "2025", 
                    "url": "https://www.vogue.com/fashion-shows/spring-2025-ready-to-wear"
                }
            ]
    
    def write_urls_to_file(self, urls: List[str], filename: str):
        """
        Write a list of URLs to a text file.
        
        Args:
            urls: List of URLs
            filename: Output filename
        """
        try:
            with open(filename, "w") as f:
                for url in urls:
                    f.write(f"{url}\n")
                    
            self.logger.info(f"Wrote {len(urls)} URLs to {filename}")
            
        except Exception as e:
            self.logger.error(f"Error writing URLs to file {filename}: {str(e)}")
            
        # Also save to Redis
        key_name = os.path.basename(filename).replace(".txt", "")
        self.storage.save_url_list(key_name, urls)