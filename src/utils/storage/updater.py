# utils/storage/updater.py
from typing import Dict, Any
from datetime import datetime
import json
from pathlib import Path
from .errors import StorageError


class DataUpdater:
    """Handles data update operations with safety checks."""

    def __init__(self, base_dir: str = None, checkpoint_file: str = None):
        self.logger = None  # Initialize logger
        self.current_file = None
        self._setup_storage(base_dir, checkpoint_file)

    def _setup_storage(self, base_dir: str, checkpoint_file: str) -> None:
        """Set up storage with base directory and checkpoint file."""
        try:
            self.base_dir = Path(base_dir) if base_dir else Path("data")
            self.base_dir.mkdir(exist_ok=True)

            if checkpoint_file:
                self.current_file = Path(checkpoint_file)
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.current_file = self.base_dir / f"data_{timestamp}.json"

        except Exception as e:
            raise StorageError(f"Storage setup failed: {str(e)}")

    def read_data(self) -> Dict[str, Any]:
        """Read data from storage file."""
        try:
            with open(self.current_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise StorageError(f"Failed to read data: {str(e)}")

    def write_data(self, data: Dict[str, Any]) -> None:
        """Write data to storage file."""
        try:
            with open(self.current_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            raise StorageError(f"Failed to write data: {str(e)}")
