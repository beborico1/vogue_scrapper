# handlers/images/images_base_handler.py
"""Base image handler with core functionality and initialization.

This module provides the base handler class with:
- Initialization and dependency injection
- Session management
- Core API methods
"""

import time
from typing import List, Dict, Optional, Any
from selenium.webdriver.remote.webdriver import WebDriver
from logging import Logger

from ...config.settings import PAGE_LOAD_WAIT
from ...exceptions.errors import ScraperError, ValidationError
from ...utils.storage.data_storage_handler import DataStorageHandler
from .slideshow_navigator import VogueSlideshowNavigator
from .look_tracker import VogueLookTracker
from .gallery_handler import VogueGalleryHandler
from .session_manager import ImageSessionManager


class VogueImagesBaseHandler:
    """Base coordinator for image collection process with session management."""

    def __init__(
        self,
        driver: WebDriver,
        logger: Logger,
        slideshow_navigator: VogueSlideshowNavigator,
        look_tracker: VogueLookTracker,
        gallery_handler: VogueGalleryHandler,
        storage_handler: DataStorageHandler,
        season_index: int,
        designer_index: int,
    ):
        """Initialize the images handler with enhanced capabilities."""
        self.driver = driver
        self.logger = logger
        self.slideshow_navigator = slideshow_navigator
        self.look_tracker = look_tracker
        self.gallery_handler = gallery_handler
        self.storage = storage_handler
        self.season_index = season_index
        self.designer_index = designer_index

        # Create session manager
        self.session_manager = ImageSessionManager(logger, storage_handler)

    def get_runway_images(self, show_url: str) -> List[Dict[str, str]]:
        """Get all runway images with enhanced session management.

        Args:
            show_url: URL of the runway show

        Returns:
            List[Dict[str, str]]: List of processed images

        Raises:
            ScraperError: If image collection fails
        """
        self.logger.info(f"Starting runway image collection: {show_url}")

        try:
            # Initialize session
            self.session_manager.initialize_session(show_url)

            # Process images
            result = self._process_runway_images()

            # Cleanup session
            self.session_manager.cleanup_session(success=True)

            return result

        except Exception as e:
            self.logger.error(f"Error in runway image collection: {str(e)}")
            self.session_manager.cleanup_session(success=False, error=str(e))
            raise ScraperError(f"Runway image collection failed: {str(e)}")

    def _process_runway_images(self) -> List[Dict[str, str]]:
        """Process all runway images with enhanced error handling.

        Returns:
            List[Dict[str, str]]: List of processed images

        Raises:
            ScraperError: If processing fails
        """
        try:
            self._navigate_to_slideshow()
            total_looks = self._get_total_looks()

            if total_looks == 0:
                raise ValidationError("No looks found to process")

            self.session_manager.update_total_looks(total_looks)
            self._update_designer_total_looks(total_looks)

            return self._collect_look_images(total_looks)

        except Exception as e:
            self.logger.error(f"Error processing runway images: {str(e)}")
            raise

    def _navigate_to_slideshow(self) -> None:
        """Navigate to slideshow view with retry capability."""
        try:
            self.driver.get(self.session_manager.get_show_url())
            time.sleep(PAGE_LOAD_WAIT)

            from .operation_handler import retry_operation

            if self.slideshow_navigator.is_slideshow_button_present():
                if not retry_operation(
                    self.logger,
                    self.slideshow_navigator.navigate_to_slideshow, 
                    "slideshow navigation"
                ):
                    from ...exceptions.errors import ElementNotFoundError
                    raise ElementNotFoundError("Failed to navigate to slideshow view")

        except Exception as e:
            self.logger.error(f"Navigation error: {str(e)}")
            raise

    def _get_total_looks(self) -> int:
        """Get total number of looks with validation.

        Returns:
            int: Total number of looks

        Raises:
            ValidationError: If total looks cannot be determined
        """
        total_looks = self.look_tracker.get_total_looks()

        if total_looks <= 0:
            raise ValidationError("Invalid total look count")

        self.logger.info(f"Total looks to process: {total_looks}")
        return total_looks

    def _update_designer_total_looks(self, total_looks: int) -> None:
        """Update designer total looks in storage.
        
        Args:
            total_looks: Total number of looks
        """
        # Implementation would go here
        pass

    def _collect_look_images(self, total_looks: int) -> List[Dict[str, str]]:
        """Import and delegate to look collector.
        
        Args:
            total_looks: Total number of looks to process

        Returns:
            List[Dict[str, str]]: List of all collected images
        """
        from .look_collector import LookCollector
        
        collector = LookCollector(
            self.logger,
            self.session_manager,
            self.gallery_handler,
            self.slideshow_navigator,
            self.storage,
            self.season_index,
            self.designer_index
        )
        
        return collector.collect_all_looks(total_looks)