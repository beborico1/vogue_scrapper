# src/utils/storage/session_storage_handler.py
"""Session management for storage operations."""

import json
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime

from .base_storage_handler import BaseStorageHandler
from ...exceptions.errors import StorageError


class SessionStorageHandler(BaseStorageHandler):
    """Handles session management and state preservation during storage operations."""

    def __init__(self, base_dir: str = None, checkpoint_file: str = None):
        """Initialize the session storage handler.

        Args:
            base_dir: Base directory for storing data files
            checkpoint_file: Optional path to checkpoint file to resume from
        """
        super().__init__(base_dir, checkpoint_file)
        self._active_session = None
        self._transaction_log = []
        self._checkpoints = {}

    def _start_designer_session(self, designer_url: str) -> None:
        """Start a new designer processing session.

        Args:
            designer_url: URL identifier of the designer

        Raises:
            StorageError: If another session is already active
        """
        if self._active_session:
            raise StorageError("Another designer session is already active")

        self._active_session = {
            "designer_url": designer_url,
            "start_time": datetime.now().isoformat(),
            "operations": [],
            "state_hash": self._calculate_state_hash(),
        }

        self.logger.info(f"Started session for designer: {designer_url}")

    def _end_designer_session(self) -> None:
        """End current designer processing session safely."""
        if self._active_session:
            end_time = datetime.now().isoformat()

            # Log session completion
            self._transaction_log.append(
                {
                    "type": "session",
                    "designer_url": self._active_session["designer_url"],
                    "start_time": self._active_session["start_time"],
                    "end_time": end_time,
                    "operations_count": len(self._active_session["operations"]),
                    "final_state_hash": self._calculate_state_hash(),
                }
            )

            self._active_session = None
            self.save_progress()
            self.logger.info("Designer session ended successfully")

    def _calculate_state_hash(self) -> str:
        """Calculate hash of current state for integrity checking."""
        try:
            current_data = self.read_data()
            data_str = json.dumps(current_data, sort_keys=True)
            return hashlib.md5(data_str.encode()).hexdigest()
        except Exception as e:
            self.logger.error(f"Error calculating state hash: {str(e)}")
            return ""

    def _create_restore_point(self) -> None:
        """Create a restore point for the current state."""
        try:
            current_data = self.read_data()
            checkpoint_hash = self._calculate_state_hash()
            self._checkpoints[checkpoint_hash] = json.dumps(current_data)

            # Keep only last 5 restore points
            if len(self._checkpoints) > 5:
                oldest_hash = list(self._checkpoints.keys())[0]
                del self._checkpoints[oldest_hash]

        except Exception as e:
            self.logger.error(f"Error creating restore point: {str(e)}")

    def _restore_from_last_point(self) -> bool:
        """Restore data from the last restore point."""
        try:
            if not self._checkpoints:
                return False

            latest_hash = list(self._checkpoints.keys())[-1]
            checkpoint_data = json.loads(self._checkpoints[latest_hash])

            self.write_data(checkpoint_data)
            self.logger.info("Successfully restored from last checkpoint")
            return True

        except Exception as e:
            self.logger.error(f"Error restoring from checkpoint: {str(e)}")
            return False

    def _log_successful_update(self) -> None:
        """Log successful data update operation."""
        if self._active_session:
            self._active_session["operations"].append(
                {
                    "type": "successful_update",
                    "timestamp": datetime.now().isoformat(),
                    "state_hash": self._calculate_state_hash(),
                }
            )

    def get_active_session_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current active session.

        Returns:
            Optional[Dict[str, Any]]: Active session info or None
        """
        if self._active_session:
            return {
                "designer_url": self._active_session["designer_url"],
                "start_time": self._active_session["start_time"],
                "operation_count": len(self._active_session["operations"]),
                "current_state_hash": self._calculate_state_hash(),
            }
        return None

    def get_transaction_log(self) -> list:
        """Get the transaction log for debugging and auditing.
        
        Returns:
            list: Transaction log entries
        """
        return self._transaction_log