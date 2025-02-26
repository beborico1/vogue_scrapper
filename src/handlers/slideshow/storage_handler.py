# src/handlers/slideshow/storage_handler.py
"""Storage operations for slideshow scraper."""

from typing import List, Dict
import json
import subprocess
from pathlib import Path

class StorageHandler:
    """Handles storage operations for slideshow data."""

    def __init__(self, storage_handler, logger):
        """Initialize the storage handler.
        
        Args:
            storage_handler: Main storage handler instance
            logger: Logger instance
        """
        self.storage = storage_handler
        self.logger = logger

    def store_look_data(self, season_index: int, designer_index: int, look_number: int, 
                        images: List[Dict[str, str]]) -> bool:
        """Store the extracted look data and mark as completed."""
        try:
            # Ensure we have valid images to store
            if not images:
                self.logger.warning(f"No images found for look {look_number}")
                return False
                
            # Log what we're trying to store for debugging
            self.logger.info(f"Storing {len(images)} images for look {look_number} (season: {season_index}, designer: {designer_index})")
            
            # Get current file path
            json_file_path = self.storage.get_current_file()
            if not json_file_path or not json_file_path.exists():
                self.logger.error("No valid JSON file to update")
                return False
                
            # Extract image URLs for emergency script
            img_urls = [img.get("url") for img in images if img.get("url")]
            
            if not img_urls:
                self.logger.error("No valid image URLs found")
                return False
            
            # Use external script for absolute reliability
            import subprocess
            cmd = [
                "python", 
                "/Users/beborico/dev/voguescrapper/src/look_updater.py",
                str(json_file_path),
                str(season_index),
                str(designer_index),
                str(look_number)
            ]
            
            # Add all image URLs to the command
            cmd.extend(img_urls)
            
            # Execute the update script as a separate process
            self.logger.info(f"Executing look updater script with {len(img_urls)} URLs")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"Look updater script success: {result.stdout}")
                
                # Make sure Redis storage is explicitly told to reimport from the temp file
                # This direct call is necessary to ensure proper synchronization
                if hasattr(self.storage, 'update_look_data'):
                    self.logger.info("Explicitly updating look data in Redis storage")
                    self.storage.update_look_data(
                        season_index=season_index,
                        designer_index=designer_index,
                        look_number=look_number,
                        images=images
                    )
                
                return True
            else:
                self.logger.error(f"Look updater script failed: {result.stderr}")
                
                # Try the storage API as fallback
                self.logger.warning("Falling back to storage API")
                return self.storage.update_look_data(
                    season_index=season_index,
                    designer_index=designer_index,
                    look_number=look_number,
                    images=images
                )

        except Exception as e:
            self.logger.error(f"Error storing look {look_number} data: {str(e)}")
            
            # One more try with the original storage method
            try:
                return self.storage.update_look_data(
                    season_index=season_index,
                    designer_index=designer_index,
                    look_number=look_number,
                    images=images
                )
            except Exception as fallback_error:
                self.logger.error(f"Fallback storage also failed: {str(fallback_error)}")
                return False