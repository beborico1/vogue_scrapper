"""Main Vogue Runway scraper implementation."""

from typing import List, Dict, Optional
from selenium.webdriver.remote.webdriver import WebDriver
from logging import Logger

from .config.settings import BASE_URL
from .handlers.auth import VogueAuthHandler
from .handlers.seasons import VogueSeasonsHandler
from .handlers.designers import VogueDesignersHandler
from .handlers.shows import VogueShowsHandler
from .handlers.images.slideshow_navigator import VogueSlideshowNavigator
from .handlers.images.look_tracker import VogueLookTracker
from .handlers.images.image_extractor import VogueImageExtractor
from .handlers.images.gallery_handler import VogueGalleryHandler
from .handlers.images.images_handler import VogueImagesHandler
from .utils.storage.storage_handler import DataStorageHandler

class VogueScraper:
    """
    A scraper for collecting fashion show data from Vogue Runway.
    Uses composition to delegate specialized tasks to handler classes.
    """
    
    def __init__(
        self,
        driver: WebDriver,
        logger: Logger,
        storage_handler: DataStorageHandler,
        base_url: str = BASE_URL
    ):
        """
        Initialize the Vogue scraper.
        
        Args:
            driver: Selenium WebDriver instance
            logger: Logger instance
            storage_handler: DataStorageHandler for real-time updates
            base_url: Base URL for Vogue website
        """
        self.driver = driver
        self.logger = logger
        self.base_url = base_url
        self.storage = storage_handler
        
        # Initialize specialized handlers
        self.auth_handler = VogueAuthHandler(driver, logger, base_url)
        self.seasons_handler = VogueSeasonsHandler(driver, logger, base_url)
        self.designers_handler = VogueDesignersHandler(driver, logger)
        self.shows_handler = VogueShowsHandler(driver, logger)
        
        # Initialize image handling components
        self.slideshow_navigator = VogueSlideshowNavigator(driver, logger)
        self.look_tracker = VogueLookTracker(driver, logger)
        self.image_extractor = VogueImageExtractor(driver, logger)
        self.gallery_handler = VogueGalleryHandler(driver, logger)
        
    def _create_images_handler(self, season_index: int, designer_index: int) -> VogueImagesHandler:
        """Create an images handler instance with current indices."""
        return VogueImagesHandler(
            driver=self.driver,
            logger=self.logger,
            slideshow_navigator=self.slideshow_navigator,
            look_tracker=self.look_tracker,
            gallery_handler=self.gallery_handler,
            storage_handler=self.storage,
            season_index=season_index,
            designer_index=designer_index
        )
        
    def authenticate(self, auth_url: str) -> bool:
        """
        Authenticate with Vogue Runway.
        
        Args:
            auth_url: Authentication URL
            
        Returns:
            bool: True if authentication successful
        """
        return self.auth_handler.authenticate(auth_url)

    def verify_authentication(self) -> bool:
        """
        Verify authentication status.
        
        Returns:
            bool: True if authenticated
        """
        return self.auth_handler.verify_authentication()

    def get_seasons_list(self) -> List[Dict[str, str]]:
        """
        Get list of all fashion show seasons.
        
        Returns:
            List[Dict[str, str]]: List of season dictionaries with keys:
                - name: Season name (e.g., "Spring 2024 Ready-to-Wear")
                - url: URL to season's shows page
        """
        return self.seasons_handler.get_seasons_list()

    def get_designers_for_season(self, season_url: str) -> List[Dict[str, str]]:
        """
        Get list of designers for a specific season.
        
        Args:
            season_url: URL for the season's page
            
        Returns:
            List[Dict[str, str]]: List of designer dictionaries with keys:
                - name: Designer name
                - url: URL to designer's show page
        """
        return self.designers_handler.get_designers_for_season(season_url)

    def get_slideshow_url(self, designer_url: str) -> Optional[str]:
        """
        Get slideshow URL from designer page.
        
        Args:
            designer_url: URL for the designer's page
            
        Returns:
            Optional[str]: URL of the slideshow or None if not found
        """
        return self.shows_handler.get_slideshow_url(designer_url)

    def get_runway_images(self, show_url: str) -> List[Dict[str, str]]:
        """
        Get all runway images from a show.
        
        Args:
            show_url: URL for the runway show
            
        Returns:
            List[Dict[str, str]]: List of image dictionaries with keys:
                - url: Image URL
                - look_number: Look number in the show
                - alt_text: Image alt text/description
        """
        return self.images_handler.get_runway_images(show_url)

    def scrape_season(self, season_url: str) -> Dict[str, List[Dict[str, str]]]:
        """
        Scrape all shows and images for a complete season.
        
        Args:
            season_url: URL for the season to scrape
            
        Returns:
            Dict[str, List[Dict[str, str]]]: Dictionary containing:
                - designers: List of designer data
                - shows: List of show data with associated images
        
        Example:
            {
                'designers': [
                    {'name': 'Designer 1', 'url': 'http://...'},
                    {'name': 'Designer 2', 'url': 'http://...'}
                ],
                'shows': [
                    {
                        'designer_name': 'Designer 1',
                        'designer_url': 'http://...',
                        'slideshow_url': 'http://...',
                        'images': [
                            {
                                'url': 'http://...',
                                'look_number': '1',
                                'alt_text': 'Look 1'
                            }
                        ]
                    }
                ]
            }
        """
        season_data = {
            'designers': [],
            'shows': []
        }
        
        # Get all designers for the season
        try:
            designers = self.get_designers_for_season(season_url)
            season_data['designers'] = designers
            self.logger.info(f"Found {len(designers)} designers for season")
            
            # Get shows and images for each designer
            for designer in designers:
                try:
                    # Get slideshow URL
                    slideshow_url = self.get_slideshow_url(designer['url'])
                    if not slideshow_url:
                        self.logger.warning(
                            f"No slideshow found for designer: {designer['name']}"
                        )
                        continue
                    
                    # Get runway images
                    self.logger.info(
                        f"Processing runway images for {designer['name']}"
                    )
                    images = self.get_runway_images(slideshow_url)
                    
                    show_data = {
                        'designer_name': designer['name'],
                        'designer_url': designer['url'],
                        'slideshow_url': slideshow_url,
                        'images': images
                    }
                    season_data['shows'].append(show_data)
                    self.logger.info(
                        f"Successfully processed {len(images)} images for "
                        f"{designer['name']}"
                    )
                    
                except Exception as e:
                    self.logger.error(
                        f"Error processing designer {designer['name']}: {str(e)}"
                    )
                    continue
            
            return season_data
            
        except Exception as e:
            self.logger.error(f"Error scraping season: {str(e)}")
            raise

    def quit(self):
        """Clean up resources and close the browser."""
        try:
            if self.driver:
                self.driver.quit()
                self.logger.info("Successfully closed browser and cleaned up resources")
        except Exception as e:
            self.logger.error(f"Error cleaning up resources: {str(e)}")