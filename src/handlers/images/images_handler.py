"""Enhanced image handler with robust error handling and session management.

This module provides a comprehensive implementation of the image handler with:
- Strong session management
- Robust error handling
- Image validation
- Progress tracking
- Retry mechanisms
"""

import time
from typing import List, Dict, Optional, Any
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    WebDriverException,
)
from logging import Logger

from ...config.settings import PAGE_LOAD_WAIT, RETRY_ATTEMPTS, RETRY_DELAY, IMAGE_RESOLUTION
from ...exceptions.errors import ElementNotFoundError, ScraperError, ValidationError
from ...utils.storage.handler import DataStorageHandler
from .slideshow_navigator import VogueSlideshowNavigator
from .look_tracker import VogueLookTracker
from .gallery_handler import VogueGalleryHandler


class VogueImagesHandler:
    """Enhanced coordinator for image collection process with session management."""

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

        # Session tracking
        self._current_session = None
        self._retry_count = 0
        self._processed_looks = set()

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
            self._initialize_session(show_url)

            # Process images
            result = self._process_runway_images()

            # Cleanup session
            self._cleanup_session(success=True)

            return result

        except Exception as e:
            self.logger.error(f"Error in runway image collection: {str(e)}")
            self._cleanup_session(success=False, error=str(e))
            raise ScraperError(f"Runway image collection failed: {str(e)}")

    def _initialize_session(self, show_url: str) -> None:
        """Initialize processing session with safety checks.

        Args:
            show_url: URL of the show to process

        Raises:
            ValidationError: If session initialization fails
        """
        try:
            # Start storage session
            self.storage._start_designer_session(show_url)

            self._current_session = {
                "show_url": show_url,
                "start_time": time.time(),
                "processed_looks": set(),
                "failed_looks": set(),
                "total_looks": 0,
                "retry_count": 0,
            }

            self.logger.info("Session initialized successfully")

        except Exception as e:
            self.logger.error(f"Session initialization failed: {str(e)}")
            raise ValidationError(f"Could not initialize session: {str(e)}")

    def _cleanup_session(self, success: bool, error: Optional[str] = None) -> None:
        """Clean up processing session safely.

        Args:
            success: Whether the session completed successfully
            error: Optional error message if session failed
        """
        try:
            if self._current_session:
                # Log session results
                duration = time.time() - self._current_session["start_time"]
                self.logger.info(
                    f"Session completed - Success: {success}, "
                    f"Duration: {duration:.2f}s, "
                    f"Processed: {len(self._current_session['processed_looks'])}, "
                    f"Failed: {len(self._current_session['failed_looks'])}"
                )

                if error:
                    self.logger.error(f"Session error: {error}")

                self._current_session = None

            # End storage session
            self.storage._end_designer_session()

        except Exception as e:
            self.logger.error(f"Error in session cleanup: {str(e)}")

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

            self._current_session["total_looks"] = total_looks
            self._update_designer_total_looks(total_looks)

            return self._collect_look_images(total_looks)

        except Exception as e:
            self.logger.error(f"Error processing runway images: {str(e)}")
            raise

    def _navigate_to_slideshow(self) -> None:
        """Navigate to slideshow view with retry capability."""
        try:
            self.driver.get(self._current_session["show_url"])
            time.sleep(PAGE_LOAD_WAIT)

            if self.slideshow_navigator.is_slideshow_button_present():
                if not self._retry_operation(
                    self.slideshow_navigator.navigate_to_slideshow, "slideshow navigation"
                ):
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

    def _collect_look_images(self, total_looks: int) -> List[Dict[str, str]]:
        """Collect images for all looks with progress tracking.

        Args:
            total_looks: Total number of looks to process

        Returns:
            List[Dict[str, str]]: List of all collected images
        """
        all_images = []
        current_look = 1

        while current_look <= total_looks:
            if current_look in self._current_session["processed_looks"]:
                self.logger.info(f"Look {current_look} already processed, skipping")
                current_look += 1
                continue

            try:
                self.logger.info(f"Processing look {current_look}/{total_looks}")

                images = self._process_single_look(current_look)
                if images:
                    all_images.extend(images)
                    self._current_session["processed_looks"].add(current_look)
                else:
                    self._current_session["failed_looks"].add(current_look)

                if current_look < total_looks:
                    if not self._navigate_to_next_look():
                        break

            except Exception as e:
                self.logger.error(f"Error processing look {current_look}: {str(e)}")
                self._current_session["failed_looks"].add(current_look)

            current_look += 1

        self._log_collection_summary(total_looks)
        return all_images

    def _process_single_look(self, look_number: int) -> Optional[List[Dict[str, str]]]:
        """Process a single look with validation and storage.

        Args:
            look_number: Number of the look to process

        Returns:
            Optional[List[Dict[str, str]]]: Processed images or None if failed
        """
        try:
            current_images = self._retry_operation(
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
        return self._retry_operation(self.slideshow_navigator.click_next, "next look navigation")

    def _retry_operation(self, operation: callable, operation_name: str) -> Any:
        """Retry an operation with exponential backoff.

        Args:
            operation: Operation to retry
            operation_name: Name of the operation for logging

        Returns:
            Any: Result of the operation
        """
        retry_count = 0
        while retry_count < RETRY_ATTEMPTS:
            try:
                result = operation()
                if result is not None:
                    return result
            except Exception as e:
                self.logger.warning(
                    f"Attempt {retry_count + 1} failed for {operation_name}: {str(e)}"
                )

            retry_count += 1
            if retry_count < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY * (2**retry_count))

        self.logger.error(f"All retry attempts failed for {operation_name}")
        return None

    def _log_collection_summary(self, total_looks: int) -> None:
        """Log summary of image collection process.

        Args:
            total_looks: Total number of looks processed
        """
        processed = len(self._current_session["processed_looks"])
        failed = len(self._current_session["failed_looks"])
        success_rate = (processed / total_looks) * 100 if total_looks > 0 else 0

        self.logger.info(
            f"Image collection complete - "
            f"Processed: {processed}/{total_looks} "
            f"({success_rate:.1f}%), "
            f"Failed: {failed}"
        )

        if failed > 0:
            self.logger.warning(f"Failed looks: {sorted(self._current_session['failed_looks'])}")
