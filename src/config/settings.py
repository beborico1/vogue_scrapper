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
AUTH_URL: str = (
    "https://link.condenast.com/click/67b7d478b993ff3a250d15f3/aHR0cHM6Ly9pZC5jb25kZW5hc3QuY29tL29pZGMvbWFnaWMtbGluaz9fc3A9Y2E2YThiZGQtM2NiMi00NDA4LTg2YjUtYTgwMWE0NmRlNzk2LjE3NDAxMDA3MTU1NjcmeGlkPWExZWJhMTRhLTNlNmQtNGJjOC1hNjIyLTJhMWVkMDk3Yzk1MiZzY29wZT1vcGVuaWQrb2ZmbGluZV9hY2Nlc3Mmc3RhdGU9JTdCJTIycmVkaXJlY3RVUkwlMjIlM0ElMjIlMkYlM0Zfc3AlM0RjYTZhOGJkZC0zY2IyLTQ0MDgtODZiNS1hODAxYTQ2ZGU3OTYuMTc0MDEwMDcxNTU2NyUyMiU3RCZwcm9tcHQ9c2VsZWN0X2FjY291bnQrY29uc2VudCZzb3VyY2U9VkVSU09fTkFWSUdBVElPTiZjbGllbnRfaWQ9Y29uZGVuYXN0LmlkZW50aXR5LmZiYzkwOTZkYzYxZjliNzljNWFjNGM4NTk5OGRhMDc1JnJlZGlyZWN0X3VyaT1odHRwcyUzQSUyRiUyRnd3dy52b2d1ZS5jb20lMkZhdXRoJTJGY29tcGxldGUmcmVzcG9uc2VfdHlwZT1jb2RlJmZpcnN0X3RpbWVfc2lnbl9pbj11bmRlZmluZWQmY29kZT1iZDFiZjM5ODRlZmU2YjQzYmNiMTgzZGUwNDdkYzYzMzJhOGJmYzhjNjk1ZmM0OGRmOGVjMTk3MTFkZGViNDli/678e7581a88d545cd703e31fC37f3df9b"
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
class StorageConfig:
    """Storage-related configuration settings."""

    BASE_DIR: str = field(default="data")
    TIMESTAMP_FORMAT: str = "%Y%m%d_%H%M%S"
    FILE_PREFIX: str = "vogue_runway"

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
        return {"base_dir": base_dir, "data_dir": base_dir / "data", "logs_dir": base_dir / "logs"}


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
    "base_dir": config.storage.BASE_DIR,
    "timestamp_format": config.storage.TIMESTAMP_FORMAT,
    "file_prefix": config.storage.FILE_PREFIX,
}

IMAGE_RESOLUTION = config.image.RESOLUTION
OUTPUT_DIR = config.output_dir
