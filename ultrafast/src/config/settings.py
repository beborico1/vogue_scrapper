"""
Ultrafast Vogue Scraper Configuration

This module contains all the configuration settings for the Ultrafast Vogue Scraper.
"""

import os
from dataclasses import dataclass
from typing import Optional, Dict, Any


# Base URLs for Vogue
BASE_URL = "https://www.vogue.com"
FASHION_SHOWS_URL = "https://www.vogue.com/fashion-shows"

# Authentication URL
AUTH_URL = "https://link.condenast.com/click/67d661334246fa3f8106b5d7/aHR0cHM6Ly9pZC5jb25kZW5hc3QuY29tL29pZGMvbWFnaWMtbGluaz9fc3A9NGVjZDdmMTEtYmM1NS00NjYwLTg3ZWYtNjdlYThkNmRjNWU0LjE3NDIwNzcyODQwNTgmeGlkPWExZWJhMTRhLTNlNmQtNGJjOC1hNjIyLTJhMWVkMDk3Yzk1MiZzY29wZT1vcGVuaWQrb2ZmbGluZV9hY2Nlc3Mmc3RhdGU9JTdCJTIycmVkaXJlY3RVUkwlMjIlM0ElMjIlMkYlM0Zfc3AlM0Q0ZWNkN2YxMS1iYzU1LTQ2NjAtODdlZi02N2VhOGQ2ZGM1ZTQuMTc0MjA3NzI4NDA1OCUyMiU3RCZwcm9tcHQ9c2VsZWN0X2FjY291bnQrY29uc2VudCZzb3VyY2U9T0lEQ19NQUdJQ19MSU5LX0VSUk9SJmNsaWVudF9pZD1jb25kZW5hc3QuaWRlbnRpdHkuZmJjOTA5NmRjNjFmOWI3OWM1YWM0Yzg1OTk4ZGEwNzUmcmVkaXJlY3RfdXJpPWh0dHBzJTNBJTJGJTJGd3d3LnZvZ3VlLmNvbSUyRmF1dGglMkZjb21wbGV0ZSZyZXNwb25zZV90eXBlPWNvZGUmZmlyc3RfdGltZV9zaWduX2luPXVuZGVmaW5lZCZjb2RlPWVmODQ4NGM1MjY4Y2RmZjM1ZWMyNjljNTcyODYxMWU5N2FmNGRlNGM2ODgzNjU3NWJkYWZkZDk2OTA3NTMyMTc/678e7581a88d545cd703e31fCb8c3d4b6"


@dataclass
class RedisConfig:
    """Redis storage configuration."""
    
    HOST: str = "localhost"
    PORT: int = 6379
    DB: int = 0
    PASSWORD: Optional[str] = None
    KEY_PREFIX: str = "ultrafast:"


@dataclass
class BrowserConfig:
    """Browser configuration settings."""
    
    # Default user agent
    USER_AGENT: str = "Fashion Research (beborico16@gmail.com)"
    # Browser window size (non-headless mode)
    WINDOW_SIZE: str = "--start-maximized"
    # Disable notifications
    DISABLE_NOTIFICATIONS: str = "--disable-notifications"
    # Implicit wait timeout
    IMPLICIT_WAIT: int = 10


@dataclass
class TimingConfig:
    """Timing-related configuration settings."""
    
    AUTH_WAIT: int = 3
    PAGE_LOAD_WAIT: int = 10  # Increased for slower loading older pages
    ELEMENT_WAIT: int = 15   # Increased for slower loading elements
    RETRY_DELAY: int = 3     # More delay between retries
    RETRY_ATTEMPTS: int = 5  # More retry attempts
    LOAD_MORE_WAIT: int = 3  # More wait time after clicking Load More
    SCROLL_PAUSE_TIME: float = 1.0  # More time to let things load during scrolling


@dataclass
class Selectors:
    """CSS selectors for elements on Vogue pages."""
    
    # Navigation elements (updated for new site structure)
    NAVIGATION_WRAPPER: str = "ChannelNavigationWrapper-iYepxT"
    NAVIGATION_HEADING: str = "GroupedNavigationGroup-bLZkwI"
    NAVIGATION_LINK: str = "a"
    
    # Designer elements
    DESIGNER_ITEM: str = "div[class*='SummaryItem']"
    DESIGNER_LINK: str = "a[class*='Link']"
    
    # Load More button
    LOAD_MORE_BUTTON: str = "Button"
    LOAD_MORE_BUTTON_LABEL: str = "Load More"
    
    # Collection sections
    SECTION_CONTAINER: str = "div[class*='Gallery']"
    SECTION_TITLE: str = "h2"
    
    # Image elements
    IMAGE_CONTAINER: str = "ResponsiveImageContainer"
    THUMBNAIL_WRAPPER: str = "div[class*='Thumbnail']"
    THUMBNAIL_CAPTION: str = "figcaption"
    LOOK_NUMBER: str = "span[class*='Look']"


@dataclass
class ImageConfig:
    """Image-related configuration settings."""
    
    # Image resolution settings for high-quality images
    RESOLUTION: Dict[str, str] = None
    
    def __post_init__(self):
        if self.RESOLUTION is None:
            self.RESOLUTION = {"original": "/w_320,", "high_res": "/w_2560,"}


class Config:
    """Main configuration class for the Ultrafast Vogue Scraper."""
    
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
        workers: int = 4
    ):
        """Initialize configuration settings."""
        # Set up Redis configuration
        self.redis = RedisConfig()
        self.redis.HOST = redis_host
        self.redis.PORT = redis_port
        self.redis.DB = redis_db
        self.redis.PASSWORD = redis_password
        
        # Set up other configurations
        self.browser = BrowserConfig()
        self.timing = TimingConfig()
        self.selectors = Selectors()
        self.image = ImageConfig()
        
        # Base URLs
        self.BASE_URL = BASE_URL
        self.FASHION_SHOWS_URL = FASHION_SHOWS_URL
        self.AUTH_URL = AUTH_URL
        
        # Parallel processing settings
        self.workers = workers
        
        # Data directories - will be set correctly in main.py
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
        
        # Load from environment variables if available
        self._load_from_env()
    
    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # Redis settings
        self.redis.HOST = os.getenv("VOGUE_REDIS_HOST", self.redis.HOST)
        self.redis.PORT = int(os.getenv("VOGUE_REDIS_PORT", str(self.redis.PORT)))
        self.redis.DB = int(os.getenv("VOGUE_REDIS_DB", str(self.redis.DB)))
        self.redis.PASSWORD = os.getenv("VOGUE_REDIS_PASSWORD", self.redis.PASSWORD)
        
        # Workers
        self.workers = int(os.getenv("VOGUE_WORKERS", str(self.workers)))