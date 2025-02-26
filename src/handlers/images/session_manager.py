# handlers/images/session_manager.py
"""Session management for image collection process.

This module provides session tracking and management with:
- Session initialization and cleanup
- Progress tracking
- Error handling
"""

import time
from typing import Optional, Set
from logging import Logger

from ...utils.storage.data_storage_handler import DataStorageHandler
from ...exceptions.errors import ValidationError


class ImageSessionManager:
    """Manages the session state for image collection process."""

    def __init__(self, logger: Logger, storage_handler: DataStorageHandler):
        """Initialize the session manager.
        
        Args:
            logger: Logger instance
            storage_handler: Data storage handler
        """
        self.logger = logger
        self.storage = storage_handler
        
        # Session state
        self._current_session = None

    def initialize_session(self, show_url: str) -> None:
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

    def cleanup_session(self, success: bool, error: Optional[str] = None) -> None:
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

    def get_show_url(self) -> str:
        """Get the current show URL.
        
        Returns:
            str: Current show URL
        
        Raises:
            ValidationError: If no active session
        """
        if not self._current_session:
            raise ValidationError("No active session")
            
        return self._current_session["show_url"]
    
    def update_total_looks(self, total_looks: int) -> None:
        """Update the total look count.
        
        Args:
            total_looks: Total number of looks
            
        Raises:
            ValidationError: If no active session
        """
        if not self._current_session:
            raise ValidationError("No active session")
            
        self._current_session["total_looks"] = total_looks
    
    def mark_look_processed(self, look_number: int) -> None:
        """Mark a look as successfully processed.
        
        Args:
            look_number: Number of the processed look
            
        Raises:
            ValidationError: If no active session
        """
        if not self._current_session:
            raise ValidationError("No active session")
            
        self._current_session["processed_looks"].add(look_number)
    
    def mark_look_failed(self, look_number: int) -> None:
        """Mark a look as failed.
        
        Args:
            look_number: Number of the failed look
            
        Raises:
            ValidationError: If no active session
        """
        if not self._current_session:
            raise ValidationError("No active session")
            
        self._current_session["failed_looks"].add(look_number)
    
    def is_look_processed(self, look_number: int) -> bool:
        """Check if a look has already been processed.
        
        Args:
            look_number: Look number to check
            
        Returns:
            bool: True if already processed
            
        Raises:
            ValidationError: If no active session
        """
        if not self._current_session:
            raise ValidationError("No active session")
            
        return look_number in self._current_session["processed_looks"]
    
    def get_processed_looks(self) -> Set[int]:
        """Get the set of processed looks.
        
        Returns:
            Set[int]: Set of processed look numbers
            
        Raises:
            ValidationError: If no active session
        """
        if not self._current_session:
            raise ValidationError("No active session")
            
        return self._current_session["processed_looks"]
    
    def get_failed_looks(self) -> Set[int]:
        """Get the set of failed looks.
        
        Returns:
            Set[int]: Set of failed look numbers
            
        Raises:
            ValidationError: If no active session
        """
        if not self._current_session:
            raise ValidationError("No active session")
            
        return self._current_session["failed_looks"]
    
    def log_collection_summary(self, total_looks: int) -> None:
        """Log summary of image collection process.

        Args:
            total_looks: Total number of looks processed
        """
        if not self._current_session:
            self.logger.warning("Attempted to log summary without active session")
            return
            
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