# utils/storage/common_interface.py
"""Common interface for storage handlers.

This module defines the common interface for all storage handlers,
ensuring consistent behavior across different storage backends.
"""

from typing import Dict, List, Any, Optional, Protocol


class StorageHandler(Protocol):
    """Protocol defining the common interface for storage handlers."""
    
    def add_season(self, season_data: Dict[str, Any]) -> bool:
        """Add or update season data.
        
        Args:
            season_data: Season data dictionary
            
        Returns:
            bool: True if successful
        """
        ...
    
    def add_designer(self, designer_data: Dict[str, Any], season: str, year: str) -> bool:
        """Add or update designer data.
        
        Args:
            designer_data: Designer data dictionary
            season: Season name
            year: Season year
            
        Returns:
            bool: True if successful
        """
        ...
    
    def add_look(self, designer_url: str, look_number: int, images: List[Dict[str, Any]]) -> bool:
        """Add or update look data.
        
        Args:
            designer_url: Designer URL identifier
            look_number: Look number
            images: List of image data dictionaries
            
        Returns:
            bool: True if successful
        """
        ...
    
    def get_season(self, season: str, year: str) -> Optional[Dict[str, Any]]:
        """Get season data by season name and year.
        
        Args:
            season: Season name
            year: Season year
            
        Returns:
            Optional[Dict[str, Any]]: Season data or None if not found
        """
        ...
    
    def get_designer(self, designer_url: str) -> Optional[Dict[str, Any]]:
        """Get designer data by URL.
        
        Args:
            designer_url: Designer URL identifier
            
        Returns:
            Optional[Dict[str, Any]]: Designer data or None if not found
        """
        ...
    
    def get_look(self, designer_url: str, look_number: int) -> Optional[Dict[str, Any]]:
        """Get look data by designer URL and look number.
        
        Args:
            designer_url: Designer URL identifier
            look_number: Look number
            
        Returns:
            Optional[Dict[str, Any]]: Look data or None if not found
        """
        ...
    
    def get_all_seasons(self) -> List[Dict[str, Any]]:
        """Get all seasons data.
        
        Returns:
            List[Dict[str, Any]]: List of season data dictionaries
        """
        ...
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata.
        
        Returns:
            Dict[str, Any]: Metadata dictionary
        """
        ...
    
    def is_season_completed(self, season: str, year: str) -> bool:
        """Check if a season has been completely processed.
        
        Args:
            season: Season name
            year: Season year
            
        Returns:
            bool: True if season completed
        """
        ...
    
    def is_designer_completed(self, designer_url: str) -> bool:
        """Check if a designer's show has been completely processed.
        
        Args:
            designer_url: Designer URL identifier
            
        Returns:
            bool: True if designer completed
        """
        ...
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scraping status and progress.
        
        Returns:
            Dict[str, Any]: Current status information
        """
        ...