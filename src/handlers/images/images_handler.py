"""
Main coordinator for the Vogue Runway image collection process.
Orchestrates the interaction between various specialized handlers
to collect and process runway show images with real-time storage.
"""

import time
from typing import List, Dict, Optional
from selenium.webdriver.remote.webdriver import WebDriver
from logging import Logger
from typing import Any

from ...config.settings import PAGE_LOAD_WAIT
from ...exceptions.errors import ElementNotFoundError
from ...utils.storage.storage_handler import DataStorageHandler
from .slideshow_navigator import VogueSlideshowNavigator
from .look_tracker import VogueLookTracker
from .gallery_handler import VogueGalleryHandler

class VogueImagesHandler:
    """Main coordinator for image collection process with real-time storage."""
    
    def __init__(
        self,
        driver: WebDriver,
        logger: Logger,
        slideshow_navigator: VogueSlideshowNavigator,
        look_tracker: VogueLookTracker,
        gallery_handler: VogueGalleryHandler,
        storage_handler: DataStorageHandler,
        season_index: int,
        designer_index: int
    ):
        """
        Initialize the images handler with pre-configured components.
        
        Args:
            driver: Selenium WebDriver instance
            logger: Logger instance
            slideshow_navigator: Configured VogueSlideshowNavigator instance
            look_tracker: Configured VogueLookTracker instance
            gallery_handler: Configured VogueGalleryHandler instance
            storage_handler: DataStorageHandler for real-time updates
            season_index: Index of current season in storage
            designer_index: Index of current designer in storage
        """
        self.driver = driver
        self.logger = logger
        self.slideshow_navigator = slideshow_navigator
        self.look_tracker = look_tracker
        self.gallery_handler = gallery_handler
        self.storage = storage_handler
        self.season_index = season_index
        self.designer_index = designer_index
        
    def get_runway_images(self, show_url: str) -> List[Dict[str, str]]:
        """Get all runway images from a show with real-time storage updates."""
        self.logger.info(f"Fetching runway images from: {show_url}")
        
        try:
            self.driver.get(show_url)
            time.sleep(PAGE_LOAD_WAIT)
            
            if self.slideshow_navigator.is_slideshow_button_present():
                self.logger.info("Found 'View Slideshow' button")
                if not self.slideshow_navigator.navigate_to_slideshow():
                    raise ElementNotFoundError("Failed to navigate to slideshow view")
            else:
                self.logger.info("No slideshow button found - assuming already in slideshow view")
            
            total_looks = self.look_tracker.get_total_looks()
            if total_looks == 0:
                raise ElementNotFoundError("Could not determine total number of looks")
                
            self.logger.info(f"Total looks to process: {total_looks}")
            
            # Update designer with total looks count
            self._update_designer_total_looks(total_looks)
            
            all_images = []
            current_look = 1
            
            while current_look <= total_looks:
                self.logger.info(f"Processing look {current_look}/{total_looks}")
                
                try:
                    current_images = self.gallery_handler.get_images_for_current_look()
                    if current_images:
                        # Real-time storage update for each look's images
                        self._store_look_images(current_look, current_images)
                        all_images.extend(current_images)
                    else:
                        self.logger.warning(f"No images found for look {current_look}")
                except Exception as e:
                    self.logger.error(f"Error processing look {current_look}: {str(e)}")
                
                if current_look < total_looks:
                    if not self.slideshow_navigator.click_next():
                        self.logger.error(f"Failed to navigate to next look at position {current_look}")
                        break
                
                current_look += 1
            
            if not all_images:
                raise ElementNotFoundError("No images found in entire show")
                
            self.logger.info(f"Successfully collected {len(all_images)} images across {total_looks} looks")
            return all_images
            
        except Exception as e:
            self.logger.error(f"Error getting runway images: {str(e)}")
            raise
            
    def _update_designer_total_looks(self, total_looks: int) -> None:
        """Update designer data with total look count."""
        try:
            self.storage.update_designer_data(
                self.season_index,
                self._get_designer_data(),
                total_looks
            )
        except Exception as e:
            self.logger.error(f"Error updating designer total looks: {str(e)}")
            
    def _store_look_images(self, look_number: int, images: List[Dict[str, str]]) -> None:
        """Store images for a specific look in real-time."""
        try:
            self.storage.update_look_data(
                self.season_index,
                self.designer_index,
                look_number,
                images
            )
        except Exception as e:
            self.logger.error(f"Error storing look images: {str(e)}")
            
    def _get_designer_data(self) -> Dict[str, Any]:
        """Get current designer data from storage."""
        try:
            current_data = self.storage.read_data()
            return current_data["seasons"][self.season_index]["designers"][self.designer_index]
        except Exception as e:
            self.logger.error(f"Error getting designer data: {str(e)}")
            return {}