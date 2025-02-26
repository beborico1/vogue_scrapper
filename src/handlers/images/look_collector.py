# handlers/images/look_collector.py
"""Look collection and processing for runway images.

This module handles collecting and processing individual looks with:
- Image extraction
- Validation
- Storage
- Navigation
"""

from typing import List, Dict, Optional
from logging import Logger

from ...utils.storage.data_storage_handler import DataStorageHandler
from .session_manager import ImageSessionManager
from .gallery_handler import VogueGalleryHandler
from .slideshow_navigator import VogueSlideshowNavigator
from .operation_handler import retry_operation


class LookCollector:
    """Collects and processes individual runway looks."""

    def __init__(
        self,
        logger: Logger,
        session_manager: ImageSessionManager,
        gallery_handler: VogueGalleryHandler,
        slideshow_navigator: VogueSlideshowNavigator,
        storage_handler: DataStorageHandler,
        season_index: int,
        designer_index: int,
    ):
        """Initialize the look collector.
        
        Args:
            logger: Logger instance
            session_manager: Session manager
            gallery_handler: Gallery handler
            slideshow_navigator: Slideshow navigator
            storage_handler: Storage handler
            season_index: Season index
            designer_index: Designer index
        """
        self.logger = logger
        self.session_manager = session_manager
        self.gallery_handler = gallery_handler
        self.slideshow_navigator = slideshow_navigator
        self.storage = storage_handler
        self.season_index = season_index
        self.designer_index = designer_index

    def collect_all_looks(self, total_looks: int) -> List[Dict[str, str]]:
        """Collect images for all looks with progress tracking.

        Args:
            total_looks: Total number of looks to process

        Returns:
            List[Dict[str, str]]: List of all collected images
        """
        all_images = []
        current_look = 1

        while current_look <= total_looks:
            if self.session_manager.is_look_processed(current_look):
                self.logger.info(f"Look {current_look} already processed, skipping")
                current_look += 1
                continue

            try:
                self.logger.info(f"Processing look {current_look}/{total_looks}")

                images = self._process_single_look(current_look)
                if images:
                    all_images.extend(images)
                    self.session_manager.mark_look_processed(current_look)
                else:
                    self.session_manager.mark_look_failed(current_look)

                if current_look < total_looks:
                    if not self._navigate_to_next_look():
                        break

            except Exception as e:
                self.logger.error(f"Error processing look {current_look}: {str(e)}")
                self.session_manager.mark_look_failed(current_look)

            current_look += 1

        self.session_manager.log_collection_summary(total_looks)
        return all_images

    def _process_single_look(self, look_number: int) -> Optional[List[Dict[str, str]]]:
        """Process a single look with validation and storage.

        Args:
            look_number: Number of the look to process

        Returns:
            Optional[List[Dict[str, str]]]: Processed images or None if failed
        """
        try:
            current_images = retry_operation(
                self.logger,
                self.gallery_handler.get_images_for_current_look,
                f"image collection for look {look_number}",
            )

            if not current_images:
                self.logger.warning(f"No images found for look {look_number}")
                return None

            if not self._validate_look_images(current_images):
                self.logger.warning(f"Image validation failed for look {look_number}")
                return None

            # Store images with validation
            if self._store_look_images(look_number, current_images):
                return current_images

            return None

        except Exception as e:
            self.logger.error(f"Error processing look {look_number}: {str(e)}")
            return None

    def _validate_look_images(self, images: List[Dict[str, str]]) -> bool:
        """Validate collected images.

        Args:
            images: List of image data to validate

        Returns:
            bool: True if images are valid
        """
        try:
            for image in images:
                if not all(key in image for key in ["url", "look_number", "alt_text"]):
                    return False

                if not image["url"] or "/verso/static/" in image["url"]:
                    return False

                if "assets.vogue.com" not in image["url"]:
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Image validation error: {str(e)}")
            return False

    def _store_look_images(self, look_number: int, images: List[Dict[str, str]]) -> bool:
        """Store look images with safety checks.

        Args:
            look_number: Number of the look
            images: List of images to store

        Returns:
            bool: True if storage successful
        """
        try:
            return self.storage.update_look_data(
                self.season_index, self.designer_index, look_number, images
            )
        except Exception as e:
            self.logger.error(f"Error storing look {look_number}: {str(e)}")
            return False

    def _navigate_to_next_look(self) -> bool:
        """Navigate to next look with retry capability.

        Returns:
            bool: True if navigation successful
        """
        return retry_operation(
            self.logger,
            self.slideshow_navigator.click_next, 
            "next look navigation"
        )