# utils/storage/session.py
from typing import Dict, Any, Optional
from datetime import datetime
import json
import hashlib
from ...exceptions.errors import StorageError


class SessionManager:
    """Manages sessions and checkpoints for data storage operations."""

    def __init__(self, logger):
        self.logger = logger
        self._active_session = None
        self._transaction_log = []
        self._checkpoints = {}

    def start_designer_session(self, designer_url: str) -> None:
        """Start a new designer processing session."""
        if self._active_session:
            raise StorageError("Another designer session is already active")

        self._active_session = {
            "designer_url": designer_url,
            "start_time": datetime.now().isoformat(),
            "operations": [],
            "state_hash": self._calculate_state_hash(),
        }
        self.logger.info(f"Started session for designer: {designer_url}")

    def end_designer_session(self) -> None:
        """End current designer processing session safely."""
        if self._active_session:
            end_time = datetime.now().isoformat()
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
            self.logger.info("Designer session ended successfully")

    def create_restore_point(self, current_data: Dict[str, Any]) -> None:
        """Create a restore point for the current state."""
        try:
            checkpoint_hash = self._calculate_state_hash(current_data)
            self._checkpoints[checkpoint_hash] = json.dumps(current_data)

            if len(self._checkpoints) > 5:
                oldest_hash = list(self._checkpoints.keys())[0]
                del self._checkpoints[oldest_hash]

        except Exception as e:
            self.logger.error(f"Error creating restore point: {str(e)}")

    def restore_from_last_point(self) -> Optional[Dict[str, Any]]:
        """Restore data from the last restore point."""
        try:
            if not self._checkpoints:
                return None

            latest_hash = list(self._checkpoints.keys())[-1]
            return json.loads(self._checkpoints[latest_hash])

        except Exception as e:
            self.logger.error(f"Error restoring from checkpoint: {str(e)}")
            return None

    def _calculate_state_hash(self, data: Dict[str, Any] = None) -> str:
        """Calculate hash of current state for integrity checking."""
        try:
            data_str = json.dumps(data, sort_keys=True)
            return hashlib.md5(data_str.encode()).hexdigest()
        except Exception as e:
            self.logger.error(f"Error calculating state hash: {str(e)}")
            return ""
