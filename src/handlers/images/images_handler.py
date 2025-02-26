# handlers/images/images_handler.py
"""Enhanced image handler with robust error handling and session management.

This module provides a comprehensive implementation of the image handler with:
- Strong session management
- Robust error handling
- Image validation
- Progress tracking
- Retry mechanisms
"""

from typing import List, Dict
from selenium.webdriver.remote.webdriver import WebDriver
from logging import Logger

from ...utils.storage.data_storage_handler import DataStorageHandler
from .slideshow_navigator import VogueSlideshowNavigator
from .look_tracker import VogueLookTracker
from .gallery_handler import VogueGalleryHandler
from .images_base_handler import VogueImagesBaseHandler


class VogueImagesHandler(VogueImagesBaseHandler):
    """Enhanced coordinator for image collection process with session management."""

    def __init__(
        self,
        driver: WebDriver,
        logger: Logger,
        slideshow_navigator: VogueSlideshowNavigator = None,
        look_tracker: VogueLookTracker = None,
        gallery_handler: VogueGalleryHandler = None,
        storage_handler: DataStorageHandler = None,
        season_index: int = 0,
        designer_index: int = 0,
    ):
        """Initialize the images handler with enhanced capabilities.
        
        This class extends VogueImagesBaseHandler with additional functionality.
        
        Args:
            driver: WebDriver instance
            logger: Logger instance
            slideshow_navigator: Optional slideshow navigator (created if None)
            look_tracker: Optional look tracker (created if None)
            gallery_handler: Optional gallery handler (created if None)
            storage_handler: Optional storage handler (created if None)
            season_index: Season index
            designer_index: Designer index
        """
        # Create default components if not provided
        if slideshow_navigator is None:
            slideshow_navigator = VogueSlideshowNavigator(driver, logger)
            
        if look_tracker is None:
            look_tracker = VogueLookTracker(driver, logger)
            
        if gallery_handler is None:
            gallery_handler = VogueGalleryHandler(driver, logger)
            
        if storage_handler is None:
            from ...utils.storage.data_storage_handler import create_default_storage
            storage_handler = create_default_storage(logger)
        
        # Initialize base class
        super().__init__(
            driver,
            logger,
            slideshow_navigator,
            look_tracker,
            gallery_handler,
            storage_handler,
            season_index,
            designer_index
        )
        
    def _update_designer_total_looks(self, total_looks: int) -> None:
        """Update designer total looks in storage.
        
        Args:
            total_looks: Total number of looks
        """
        try:
            self.storage.update_designer_metadata(
                self.season_index,
                self.designer_index,
                {"total_looks": total_looks}
            )
        except Exception as e:
            self.logger.error(f"Error updating designer total looks: {str(e)}")


# Convenience factory method
def create_images_handler(
    driver: WebDriver,
    logger: Logger,
    season_index: int = 0,
    designer_index: int = 0
) -> VogueImagesHandler:
    """Create a preconfigured images handler.
    
    Args:
        driver: WebDriver instance
        logger: Logger instance
        season_index: Season index
        designer_index: Designer index
        
    Returns:
        VogueImagesHandler: Configured handler
    """
    return VogueImagesHandler(
        driver=driver,
        logger=logger,
        season_index=season_index,
        designer_index=designer_index
    )