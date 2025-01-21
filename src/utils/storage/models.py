"""Data models and type definitions for runway data storage."""

from typing import TypedDict, List, Optional
from datetime import datetime

class ImageData(TypedDict):
    """Type definition for image data."""
    url: str
    alt_text: str
    type: str
    timestamp: str

class LookData(TypedDict):
    """Type definition for look data."""
    look_number: int
    completed: bool
    images: List[ImageData]

class DesignerData(TypedDict):
    """Type definition for designer data."""
    name: str
    url: str
    total_looks: int
    extracted_looks: int
    completed: bool
    looks: List[LookData]

class SeasonData(TypedDict):
    """Type definition for season data."""
    season: str
    year: str
    completed: bool
    total_designers: int
    completed_designers: int
    designers: List[DesignerData]