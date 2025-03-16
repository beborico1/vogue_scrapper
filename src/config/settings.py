# src/config/settings.py

"""
Configuration settings for the Vogue runway scraper.

This module contains all configuration settings including URLs,
browser settings, timing configurations, storage settings, and CSS selectors.
All configuration constants are centralized here for easy maintenance.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from typing import ClassVar
from datetime import datetime
from pathlib import Path

# Base URLs and authentication
BASE_URL: str = "https://www.vogue.com"
FASHION_SHOWS_URL: str = "https://www.vogue.com/fashion-shows"
AUTH_URL: str = (
"https://link.condenast.com/click/67d534dbbb8ce38f3a09e5e0/aHR0cHM6Ly9pZC5jb25kZW5hc3QuY29tL29pZGMvbWFnaWMtbGluaz9fc3A9MTk0MTg4NjgtYWFhZC00MmZkLTgxZjktNzE2YjI1OTg1ZWJhLjE3NDE4NzU4ODExNjAmeGlkPWU1MzIyNWFkLWU1M2QtNDI4MS1hNGFlLTM4NGM2OGIwM2ZlYSZzY29wZT1vcGVuaWQrb2ZmbGluZV9hY2Nlc3Mmc3RhdGU9JTdCJTIycmVkaXJlY3RVUkwlMjIlM0ElMjIlMkYlM0Zfc3AlM0QxOTQxODg2OC1hYWFkLTQyZmQtODFmOS03MTZiMjU5ODVlYmEuMTc0MTg3NTg4MTE2MCUyMiU3RCZwcm9tcHQ9c2VsZWN0X2FjY291bnQrY29uc2VudCZzb3VyY2U9T0lEQ19NQUdJQ19MSU5LX0VSUk9SJmNsaWVudF9pZD1jb25kZW5hc3QuaWRlbnRpdHkuZmJjOTA5NmRjNjFmOWI3OWM1YWM0Yzg1OTk4ZGEwNzUmcmVkaXJlY3RfdXJpPWh0dHBzJTNBJTJGJTJGd3d3LnZvZ3VlLmNvbSUyRmF1dGglMkZjb21wbGV0ZSZyZXNwb25zZV90eXBlPWNvZGUmZmlyc3RfdGltZV9zaWduX2luPXVuZGVmaW5lZCZjb2RlPWM3NjQ5N2U0MTNhM2E5ZWQzNjNiNGViNThiZGU4YzI3MThhYjJkNzczNzhhOWZmMjQ2ZTQ2YjY5ZDViYTAyMmY/678e7581a88d545cd703e31fC4c11e561"
)


# Default browser options
def get_default_browser_options() -> Dict[str, str]:
    """Get default browser options."""
    return {
        "user_agent": "Fashion Research (beborico16@gmail.com)",
        "window_size": "--start-maximized",
        "notifications": "--disable-notifications",
    }


@dataclass
class BrowserConfig:
    """Browser configuration settings."""

    OPTIONS: Dict[str, str] = field(default_factory=get_default_browser_options)
    IMPLICIT_WAIT: int = 10


@dataclass
class TimingConfig:
    """Timing-related configuration settings."""

    AUTH_WAIT: int = 3
    PAGE_LOAD_WAIT: int = 5
    ELEMENT_WAIT: int = 10
    RETRY_DELAY: int = 2
    RETRY_ATTEMPTS: int = 3


@dataclass
class Selectors:
    """CSS selectors and class names."""

    # Navigation elements
    navigation_wrapper: ClassVar[str] = "NavigationWrapper-bFftAs"
    navigation_heading: ClassVar[str] = "NavigationHeadingWrapper-befTuI"
    navigation_link: ClassVar[str] = "NavigationInternalLink-cWEaeo"

    # Designer elements
    designer_item: ClassVar[str] = "SummaryItemWrapper-iwvBff"
    designer_link: ClassVar[str] = "SummaryItemHedLink-civMjp"

    # Image elements
    image_container: ClassVar[str] = "ResponsiveImageContainer-eybHBd"
    look_number: ClassVar[str] = "RunwayGalleryLookNumberText-hidXa"


def get_default_image_resolution() -> Dict[str, str]:
    """Get default image resolution settings."""
    return {"original": "/w_320,", "high_res": "/w_2560,"}


@dataclass
class RedisConfig:
    """Redis storage configuration."""
    
    HOST: str = "localhost"
    PORT: int = 6379
    DB: int = 0
    PASSWORD: Optional[str] = None
    KEY_PREFIX: str = "vogue:"
    CONNECTION_POOL_MAX: int = 10


@dataclass
class StorageConfig:
    """Storage-related configuration settings."""

    # Storage mode (json or redis)
    STORAGE_MODE: str = "redis"# "json"
    
    # General settings
    BASE_DIR: str = field(default="data")
    TIMESTAMP_FORMAT: str = "%Y%m%d_%H%M%S"
    FILE_PREFIX: str = "vogue_data"
    
    # Redis specific settings
    REDIS: RedisConfig = field(default_factory=RedisConfig)

    @property
    def default_data_structure(self) -> Dict[str, Any]:
        """Get default data structure for storage."""
        return {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "overall_progress": {
                    "total_seasons": 0,
                    "completed_seasons": 0,
                    "total_designers": 0,
                    "completed_designers": 0,
                    "total_looks": 0,
                    "extracted_looks": 0,
                },
            },
            "seasons": [],
        }


@dataclass
class ImageConfig:
    """Image-related configuration settings."""

    RESOLUTION: Dict[str, str] = field(default_factory=get_default_image_resolution)


class Config:
    """Main configuration class that brings all settings together."""

    def __init__(self):
        """Initialize configuration settings."""
        self.browser = BrowserConfig()
        self.timing = TimingConfig()
        self.selectors = Selectors()
        self.image = ImageConfig()
        self.storage = StorageConfig()
        self.output_dir = os.getenv("VOGUE_OUTPUT_DIR", "data")
        
        # Add base URLs
        self.BASE_URL = BASE_URL
        self.FASHION_SHOWS_URL = FASHION_SHOWS_URL
        self.AUTH_URL = AUTH_URL
        
        # Add sorting configuration
        self.sorting_type = os.getenv("VOGUE_SORTING_TYPE", "desc")  # Default to descending (newest first)
        
        # Load environment variables for configuration
        self._load_from_env()
        
    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # Storage mode
        self.storage.STORAGE_MODE = os.getenv("VOGUE_STORAGE_MODE", self.storage.STORAGE_MODE)
        
        # Redis settings
        self.storage.REDIS.HOST = os.getenv("VOGUE_REDIS_HOST", self.storage.REDIS.HOST)
        self.storage.REDIS.PORT = int(os.getenv("VOGUE_REDIS_PORT", str(self.storage.REDIS.PORT)))
        self.storage.REDIS.DB = int(os.getenv("VOGUE_REDIS_DB", str(self.storage.REDIS.DB)))
        self.storage.REDIS.PASSWORD = os.getenv("VOGUE_REDIS_PASSWORD", self.storage.REDIS.PASSWORD)
        
        # Output directory
        self.output_dir = os.getenv("VOGUE_OUTPUT_DIR", self.output_dir)
        
        # Sorting type (asc or desc)
        self.sorting_type = os.getenv("VOGUE_SORTING_TYPE", self.sorting_type)

    @property
    def chrome_options(self) -> Dict[str, str]:
        """Get Chrome browser options."""
        return self.browser.OPTIONS

    @property
    def wait_times(self) -> Dict[str, int]:
        """Get all wait time configurations."""
        return {
            "implicit_wait": self.browser.IMPLICIT_WAIT,
            "auth_wait": self.timing.AUTH_WAIT,
            "page_load_wait": self.timing.PAGE_LOAD_WAIT,
            "element_wait": self.timing.ELEMENT_WAIT,
        }

    @property
    def storage_paths(self) -> Dict[str, Path]:
        """Get storage-related paths."""
        base_dir = Path(self.storage.BASE_DIR)
        return {"base_dir": base_dir, "data_dir": base_dir, "logs_dir": Path("logs")}

    @property
    def is_redis_storage(self) -> bool:
        """Check if storage mode is Redis."""
        return self.storage.STORAGE_MODE.lower() == "redis"


# Create a global config instance
config = Config()

# For backwards compatibility and easier imports
CHROME_OPTIONS = config.chrome_options
IMPLICIT_WAIT = config.browser.IMPLICIT_WAIT
AUTH_WAIT = config.timing.AUTH_WAIT
PAGE_LOAD_WAIT = config.timing.PAGE_LOAD_WAIT
ELEMENT_WAIT = config.timing.ELEMENT_WAIT
RETRY_ATTEMPTS = config.timing.RETRY_ATTEMPTS
RETRY_DELAY = config.timing.RETRY_DELAY

# Create SELECTORS dictionary from Selectors class variables
SELECTORS = {
    "navigation_wrapper": Selectors.navigation_wrapper,
    "navigation_heading": Selectors.navigation_heading,
    "navigation_link": Selectors.navigation_link,
    "designer_item": Selectors.designer_item,
    "designer_link": Selectors.designer_link,
    "image_container": Selectors.image_container,
    "look_number": Selectors.look_number,
}

# Storage settings
STORAGE = {
    "mode": config.storage.STORAGE_MODE,
    "base_dir": config.storage.BASE_DIR,
    "timestamp_format": config.storage.TIMESTAMP_FORMAT,
    "file_prefix": config.storage.FILE_PREFIX,
    "redis": {
        "host": config.storage.REDIS.HOST,
        "port": config.storage.REDIS.PORT,
        "db": config.storage.REDIS.DB,
        "password": config.storage.REDIS.PASSWORD,
        "key_prefix": config.storage.REDIS.KEY_PREFIX,
    }
}

IMAGE_RESOLUTION = config.image.RESOLUTION
OUTPUT_DIR = config.output_dir
