# utils/storage/models.py
"""Data models for storage.

This module defines the data models and schema for both JSON and Redis storage,
ensuring consistent data structures across the application.
"""

from typing import TypedDict, List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


# Original TypedDict models for JSON storage

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


# Dataclass models for Redis storage

@dataclass
class Image:
    """Image data model for Redis."""
    
    url: str
    look_number: int
    alt_text: str = ""
    type: str = "default"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "look_number": self.look_number,
            "alt_text": self.alt_text,
            "type": self.type,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Image':
        """Create image from dictionary."""
        return cls(
            url=data["url"],
            look_number=data["look_number"],
            alt_text=data.get("alt_text", ""),
            type=data.get("type", "default"),
            timestamp=data.get("timestamp", datetime.now().isoformat())
        )


@dataclass
class Look:
    """Look data model for Redis."""
    
    look_number: int
    images: List[Image] = field(default_factory=list)
    completed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "look_number": self.look_number,
            "images": [img.to_dict() for img in self.images],
            "completed": self.completed
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Look':
        """Create look from dictionary."""
        look = cls(
            look_number=data["look_number"],
            completed=data.get("completed", False)
        )
        look.images = [Image.from_dict(img) for img in data.get("images", [])]
        return look


@dataclass
class Designer:
    """Designer data model for Redis."""
    
    name: str
    url: str
    slideshow_url: Optional[str] = None
    total_looks: int = 0
    extracted_looks: int = 0
    completed: bool = False
    looks: List[Look] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "url": self.url,
            "slideshow_url": self.slideshow_url,
            "total_looks": self.total_looks,
            "extracted_looks": self.extracted_looks,
            "completed": self.completed,
            "looks": [look.to_dict() for look in self.looks]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Designer':
        """Create designer from dictionary."""
        designer = cls(
            name=data["name"],
            url=data["url"],
            slideshow_url=data.get("slideshow_url"),
            total_looks=data.get("total_looks", 0),
            extracted_looks=data.get("extracted_looks", 0),
            completed=data.get("completed", False)
        )
        designer.looks = [Look.from_dict(look) for look in data.get("looks", [])]
        return designer


@dataclass
class Season:
    """Season data model for Redis."""
    
    season: str
    year: str
    url: str
    total_designers: int = 0
    completed_designers: int = 0
    completed: bool = False
    designers: List[Designer] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "season": self.season,
            "year": self.year,
            "url": self.url,
            "total_designers": self.total_designers,
            "completed_designers": self.completed_designers,
            "completed": self.completed,
            "designers": [designer.to_dict() for designer in self.designers]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Season':
        """Create season from dictionary."""
        season = cls(
            season=data["season"],
            year=data["year"],
            url=data["url"],
            total_designers=data.get("total_designers", 0),
            completed_designers=data.get("completed_designers", 0),
            completed=data.get("completed", False)
        )
        season.designers = [Designer.from_dict(designer) for designer in data.get("designers", [])]
        return season


@dataclass
class Progress:
    """Progress tracking model for Redis."""
    
    total_seasons: int = 0
    completed_seasons: int = 0
    total_designers: int = 0
    completed_designers: int = 0
    total_looks: int = 0
    extracted_looks: int = 0
    completion_percentage: float = 0.0
    extraction_rate: float = 0.0
    estimated_completion: Optional[str] = None
    start_time: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_seasons": self.total_seasons,
            "completed_seasons": self.completed_seasons,
            "total_designers": self.total_designers,
            "completed_designers": self.completed_designers,
            "total_looks": self.total_looks,
            "extracted_looks": self.extracted_looks,
            "completion_percentage": self.completion_percentage,
            "extraction_rate": self.extraction_rate,
            "estimated_completion": self.estimated_completion,
            "start_time": self.start_time
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Progress':
        """Create progress from dictionary."""
        return cls(
            total_seasons=data.get("total_seasons", 0),
            completed_seasons=data.get("completed_seasons", 0),
            total_designers=data.get("total_designers", 0),
            completed_designers=data.get("completed_designers", 0),
            total_looks=data.get("total_looks", 0),
            extracted_looks=data.get("extracted_looks", 0),
            completion_percentage=data.get("completion_percentage", 0.0),
            extraction_rate=data.get("extraction_rate", 0.0),
            estimated_completion=data.get("estimated_completion"),
            start_time=data.get("start_time")
        )


@dataclass
class Metadata:
    """Metadata model for Redis storage."""
    
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    overall_progress: Progress = field(default_factory=Progress)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "overall_progress": self.overall_progress.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Metadata':
        """Create metadata from dictionary."""
        return cls(
            created_at=data.get("created_at", datetime.now().isoformat()),
            last_updated=data.get("last_updated", datetime.now().isoformat()),
            overall_progress=Progress.from_dict(data.get("overall_progress", {}))
        )
