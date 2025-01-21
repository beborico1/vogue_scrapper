"""Main entry point for Vogue Runway scraper with real-time storage."""

from typing import Dict, Optional, List
from src.scraper import VogueScraper
from src.utils.driver import setup_chrome_driver
from src.utils.logging import setup_logger
from src.utils.storage.storage_handler import DataStorageHandler
from src.config.settings import BASE_URL, AUTH_URL
from src.exceptions.errors import AuthenticationError, ScraperError

class VogueRunwayScraper:
    """Main scraper orchestrator class with real-time data storage."""
    
    def __init__(self):
        """Initialize the scraper orchestrator."""
        self.logger = setup_logger()
        self.storage = DataStorageHandler()
        self.driver = None
        self.scraper = None
        self.current_file = "vogue_runway_20250120_191830.json" # None

    def initialize_scraper(self) -> None:
        """Initialize the Selenium driver and VogueScraper."""
        try:
            print("3") # ... remove
            self.driver = setup_chrome_driver()
            print("4") # ... remove
            self.scraper = VogueScraper(
                driver=self.driver,
                logger=self.logger,
                storage_handler=self.storage,
                base_url=BASE_URL
            )
            print("5") # ... remove
            self.logger.info("Scraper initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize scraper: {str(e)}")
            raise

    def _get_season_index(self, season: Dict[str, str]) -> Optional[int]:
        """Get index of season in storage or None if not found."""
        if not self.current_file:
            return None
            
        current_data = self.storage.read_data()
        for i, stored_season in enumerate(current_data["seasons"]):
            if (stored_season["season"] == season["season"] and 
                stored_season["year"] == season["year"]):
                return i
        return None

    def process_season(self, season: Dict[str, str]) -> None:
        """Process a single season's data with real-time storage."""
        self.logger.info(f"Processing season: {season['season']} {season['year']}")
        
        try:
            # Check if season exists in storage
            season_index = self._get_season_index(season)
            if season_index is None:
                # Save initial season data
                season_data = {
                    'season': season['season'],
                    'year': season['year'],
                    'url': season['url']
                }
                self.storage.update_season_data(season_data)
                season_index = len(self.storage.read_data()["seasons"]) - 1
            
            # Get designers if not already processed
            if not self.storage.is_season_completed(season):
                designers = self.scraper.get_designers_for_season(season['url'])
                
                for designer_index, designer in enumerate(designers):
                    if not self.storage.is_designer_completed(designer['url']):
                        self.logger.info(f"Processing designer: {designer['name']}")
                        
                        try:
                            # Get slideshow URL
                            slideshow_url = self.scraper.get_slideshow_url(designer['url'])
                            if not slideshow_url:
                                self.logger.warning(
                                    f"No slideshow found for designer: {designer['name']}"
                                )
                                continue
                            
                            # Create designer data
                            designer_data = {
                                'name': designer['name'],
                                'url': designer['url'],
                                'slideshow_url': slideshow_url
                            }
                            
                            # Save initial designer data
                            self.storage.update_designer_data(
                                season_index,
                                designer_data,
                                0  # Total looks will be updated during image processing
                            )
                            
                            # Process runway images with real-time updates
                            images_handler = self.scraper._create_images_handler(
                                season_index,
                                designer_index
                            )
                            images_handler.get_runway_images(slideshow_url)
                            
                        except Exception as e:
                            self.logger.error(
                                f"Error processing designer {designer['name']}: {str(e)}"
                            )
                            continue
            else:
                self.logger.info(f"Season already completed: {season['season']} {season['year']}")
                
        except Exception as e:
            self.logger.error(
                f"Error processing season {season['season']} {season['year']}: {str(e)}"
            )
            raise

    def resume_from_checkpoint(self) -> None:
        """Resume scraping from last checkpoint in storage."""
        try:
            current_data = self.storage.read_data()
            
            # Find first incomplete season
            for season_index, season in enumerate(current_data["seasons"]):
                if not season.get("completed", False):
                    self.logger.info(
                        f"Resuming from season: {season['season']} {season['year']}"
                    )
                    return season_index, season
                    
            # All seasons completed
            return None, None
            
        except Exception as e:
            self.logger.error(f"Error reading checkpoint: {str(e)}")
            return None, None

    def run(self) -> None:
        """Execute the main scraping process with real-time storage."""
        self.logger.info("=== Starting Vogue Scraper ===")
        
        try:
            # Initialize storage
            self.current_file = self.storage.initialize_file()
            print("1", self.current_file) # ... remove
            
            # Initialize scraper and authenticate
            self.initialize_scraper()
            print("2", self.scraper) # ... remove
            if not self.scraper.authenticate(AUTH_URL):
                raise AuthenticationError("Failed to authenticate with Vogue")
            
            # Check for existing progress
            checkpoint = self.resume_from_checkpoint()
            if checkpoint[0] is not None:
                start_index = checkpoint[0]
                self.logger.info("Resuming from previous checkpoint")
            else:
                start_index = 0
                # Get all seasons
                seasons = self.scraper.get_seasons_list()
                if not seasons:
                    self.logger.error("No seasons found")
                    return
                
                self.logger.info(f"Found {len(seasons)} seasons")
                
                # Save all season metadata
                for season in seasons:
                    self.storage.update_season_data(season)
            
            # Process seasons from checkpoint
            current_data = self.storage.read_data()
            for season_index in range(start_index, len(current_data["seasons"])):
                try:
                    season = current_data["seasons"][season_index]
                    self.process_season(season)
                except ScraperError as e:
                    self.logger.error(str(e))
                    continue
                    
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            
        finally:
            if self.driver:
                self.driver.quit()
        
        self.logger.info("=== Vogue Scraper Complete ===")

def main():
    """Main entry point."""
    scraper = VogueRunwayScraper()
    scraper.run()

if __name__ == "__main__":
    main()