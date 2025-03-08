"""Enhanced image handler with robust error handling and session management.

This module provides a comprehensive implementation of the image handler with:
- Strong data validation
- Session-based processing
- Atomic updates
- Error recovery
- Explicit waiting mechanisms
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from ...exceptions.errors import ScraperError, StorageError
from ...config.settings import PAGE_LOAD_WAIT, ELEMENT_WAIT
from ..images.operation_handler import retry_operation, safe_operation


class VogueImagesHandler:
    """Enhanced coordinator for image collection process with session management."""

    def __init__(
        self,
        driver, 
        logger, 
        slideshow_navigator=None, 
        look_tracker=None, 
        gallery_handler=None, 
        storage_handler=None, 
        season_index=0, 
        designer_index=0
    ):
        """Initialize the images handler with enhanced capabilities."""
        self.driver = driver
        self.logger = logger
        
        # Initialize components if not provided
        if slideshow_navigator is None:
            from ..images.slideshow_navigator import VogueSlideshowNavigator
            slideshow_navigator = VogueSlideshowNavigator(driver, logger)
            
        if look_tracker is None:
            from ..images.look_tracker import VogueLookTracker
            look_tracker = VogueLookTracker(driver, logger)
            
        if gallery_handler is None:
            from ..images.gallery_handler import VogueGalleryHandler
            gallery_handler = VogueGalleryHandler(driver, logger)
            
        if storage_handler is None:
            from ...utils.storage.data_storage_handler import create_default_storage
            storage_handler = create_default_storage(logger)
        
        self.slideshow_navigator = slideshow_navigator
        self.look_tracker = look_tracker
        self.gallery_handler = gallery_handler
        self.storage = storage_handler
        
        self.season_index = season_index
        self.designer_index = designer_index
        
        # Session management
        self._active_session = None
        self._processed_looks = set()
        self._failed_looks = set()

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

            self._active_session = {
                "show_url": show_url,
                "start_time": datetime.now(),
                "processed_looks": set(),
                "failed_looks": set(),
                "total_looks": 0,
                "retry_count": 0,
            }

            self.logger.info("Session initialized successfully")

        except Exception as e:
            self.logger.error(f"Session initialization failed: {str(e)}")
            raise ScraperError(f"Could not initialize session: {str(e)}")

    def _cleanup_session(self, success: bool, error: Optional[str] = None) -> None:
        """Clean up processing session safely.

        Args:
            success: Whether the session completed successfully
            error: Optional error message if session failed
        """
        try:
            if self._active_session:
                # Log session results
                duration = (datetime.now() - self._active_session["start_time"]).total_seconds()
                self.logger.info(
                    f"Session completed - Success: {success}, "
                    f"Duration: {duration:.2f}s, "
                    f"Processed: {len(self._active_session['processed_looks'])}, "
                    f"Failed: {len(self._active_session['failed_looks'])}"
                )

                if error:
                    self.logger.error(f"Session error: {error}")

                self._active_session = None

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
            # Navigate to slideshow with retry
            navigation_success = retry_operation(
                self.logger,
                self.slideshow_navigator.navigate_to_slideshow,
                "slideshow navigation"
            )
            
            if not navigation_success:
                raise ScraperError("Failed to navigate to slideshow view")
                
            # Ensure the gallery is loaded
            WebDriverWait(self.driver, PAGE_LOAD_WAIT).until(
                EC.presence_of_element_located((By.CLASS_NAME, "RunwayGalleryImageCollection"))
            )
            
            # Get total number of looks with validation
            total_looks = self._get_total_looks()
            if total_looks <= 0:
                raise ScraperError("No looks found or invalid count")

            # Update session and storage with total looks
            self._update_session_total_looks(total_looks)
            self._update_designer_total_looks(total_looks)

            # Use fast batch look collection when possible
            all_look_urls = self.slideshow_navigator.extract_all_look_urls(total_looks)
            if all_look_urls and len(all_look_urls) > 0:
                self.logger.info(f"Using fast batch collection for {len(all_look_urls)} looks")
                return self._collect_looks_in_batch(all_look_urls)
            else:
                self.logger.info(f"Using sequential collection for {total_looks} looks")
                return self._collect_looks_sequentially(total_looks)

        except Exception as e:
            self.logger.error(f"Error processing runway images: {str(e)}")
            raise

    def _get_total_looks(self) -> int:
        """Get total number of looks with validation.

        Returns:
            int: Total number of looks

        Raises:
            ScraperError: If total looks cannot be determined
        """
        try:
            # Wait for look number element to be present
            WebDriverWait(self.driver, ELEMENT_WAIT).until(
                EC.presence_of_element_located((By.CLASS_NAME, "RunwayGalleryLookNumberText-hidXa"))
            )
            
            total_looks = self.look_tracker.get_total_looks()

            if total_looks <= 0:
                raise ScraperError("Invalid total look count")

            self.logger.info(f"Total looks to process: {total_looks}")
            return total_looks
            
        except TimeoutException:
            raise ScraperError("Look number element not found")
        except Exception as e:
            raise ScraperError(f"Error getting total looks: {str(e)}")

    def _update_session_total_looks(self, total_looks: int) -> None:
        """Update session with total look count.
        
        Args:
            total_looks: Total number of looks
        """
        if self._active_session:
            self._active_session["total_looks"] = total_looks

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

    def _collect_looks_in_batch(self, look_urls: Dict[int, str]) -> List[Dict[str, str]]:
        """Collect looks in parallel batch using URLs.
        
        Args:
            look_urls: Dictionary mapping look numbers to URLs
            
        Returns:
            List of collected images
        """
        all_images = []
        
        # Create progress tracking
        total_looks = len(look_urls)
        processed_count = 0
        failed_count = 0
        
        # Process all URLs in sorted order
        for look_number, url in sorted(look_urls.items()):
            # Skip already processed looks
            if look_number in self._active_session.get("processed_looks", set()):
                self.logger.info(f"Look {look_number} already processed, skipping")
                processed_count += 1
                continue
                
            try:
                # Navigate to the URL
                self.driver.get(url)
                
                # Wait for gallery to load
                WebDriverWait(self.driver, PAGE_LOAD_WAIT).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "RunwayGalleryImageCollection"))
                )
                
                # Extract images for this look with retry
                images = retry_operation(
                    self.logger,
                    self.gallery_handler.get_images_for_current_look,
                    f"image extraction for look {look_number}"
                )
                
                if images:
                    all_images.extend(images)
                    
                    # Store the look data
                    storage_success = self.storage.update_look_data(
                        self.season_index,
                        self.designer_index,
                        look_number,
                        images
                    )
                    
                    if storage_success:
                        # Mark as processed
                        self._active_session.get("processed_looks", set()).add(look_number)
                        processed_count += 1
                        # Log progress at regular intervals
                        if processed_count % 5 == 0 or processed_count == total_looks:
                            self.logger.info(f"Progress: {processed_count}/{total_looks} looks processed")
                    else:
                        # Mark as failed
                        self._active_session.get("failed_looks", set()).add(look_number)
                        failed_count += 1
                        self.logger.error(f"Failed to store data for look {look_number}")
                else:
                    # Mark as failed
                    self._active_session.get("failed_looks", set()).add(look_number)
                    failed_count += 1
                    self.logger.error(f"No images found for look {look_number}")
                    
            except Exception as e:
                # Mark as failed
                self._active_session.get("failed_looks", set()).add(look_number)
                failed_count += 1
                self.logger.error(f"Error processing look {look_number}: {str(e)}")
        
        # Log final summary
        self.logger.info(f"Batch processing complete: {processed_count} processed, {failed_count} failed")
        return all_images

    def _collect_looks_sequentially(self, total_looks: int) -> List[Dict[str, str]]:
        """Collect looks sequentially by navigation.
        
        Args:
            total_looks: Total number of looks
            
        Returns:
            List of collected images
        """
        all_images = []
        current_look = 1
        
        while current_look <= total_looks:
            # Skip already processed looks
            if current_look in self._active_session.get("processed_looks", set()):
                self.logger.info(f"Look {current_look} already processed, skipping")
                
                # Navigate to next look if not at end
                if current_look < total_looks:
                    if not self.slideshow_navigator.click_next():
                        self.logger.error(f"Failed to navigate to next look after {current_look}")
                        break
                
                current_look += 1
                continue
                
            try:
                self.logger.info(f"Processing look {current_look}/{total_looks}")
                
                # Wait for gallery to load
                WebDriverWait(self.driver, PAGE_LOAD_WAIT).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "RunwayGalleryImageCollection"))
                )
                
                # Extract images for this look with retry
                images = retry_operation(
                    self.logger,
                    self.gallery_handler.get_images_for_current_look,
                    f"image extraction for look {current_look}"
                )
                
                if images:
                    all_images.extend(images)
                    
                    # Store the look data
                    storage_success = self.storage.update_look_data(
                        self.season_index,
                        self.designer_index,
                        current_look,
                        images
                    )
                    
                    if storage_success:
                        # Mark as processed
                        self._active_session.get("processed_looks", set()).add(current_look)
                    else:
                        # Mark as failed
                        self._active_session.get("failed_looks", set()).add(current_look)
                        self.logger.error(f"Failed to store data for look {current_look}")
                else:
                    # Mark as failed
                    self._active_session.get("failed_looks", set()).add(current_look)
                    self.logger.error(f"No images found for look {current_look}")
                
                # Navigate to next look if not at end
                if current_look < total_looks:
                    navigation_success = retry_operation(
                        self.logger,
                        self.slideshow_navigator.click_next,
                        f"navigation to look {current_look + 1}"
                    )
                    
                    if not navigation_success:
                        self.logger.error(f"Failed to navigate to next look after {current_look}")
                        break
                
            except Exception as e:
                # Mark as failed
                self._active_session.get("failed_looks", set()).add(current_look)
                self.logger.error(f"Error processing look {current_look}: {str(e)}")
                
                # Try to recover by navigating to next look
                if current_look < total_looks:
                    try:
                        self.slideshow_navigator.click_next()
                    except:
                        self.logger.error("Failed to recover by navigating to next look")
                        break
            
            current_look += 1
        
        # Log final summary
        processed_count = len(self._active_session.get("processed_looks", set()))
        failed_count = len(self._active_session.get("failed_looks", set()))
        self.logger.info(f"Sequential processing complete: {processed_count}/{total_looks} processed, {failed_count} failed")
        
        return all_images