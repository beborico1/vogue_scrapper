# utils/storage/data_utils.py
"""Data manipulation and processing utilities for storage operations.

This module provides specialized functions for data type handling, 
look operations, and direct manipulation of storage data.
"""

import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

from src.exceptions.errors import FileOperationError


def determine_image_type(alt_text: str) -> str:
    """Determine the type of image based on its alt text.

    Args:
        alt_text: Alt text from the image

    Returns:
        str: Image type ('back', 'detail', or 'front')

    Example:
        >>> determine_image_type("Back view of Look 1")
        'back'
    """
    alt_lower = alt_text.lower()
    if "back" in alt_lower:
        return "back"
    elif "detail" in alt_lower:
        return "detail"
    else:
        return "front"


def directly_add_look(json_file_path: Union[str, Path], 
                      season_index: int, 
                      designer_index: int, 
                      look_number: int, 
                      images: List[Dict[str, str]]) -> bool:
    """
    Directly add a look to the JSON file, bypassing all storage handlers.
    
    Args:
        json_file_path: Path to the JSON file
        season_index: Index of the season
        designer_index: Index of the designer
        look_number: Look number
        images: List of image data
        
    Returns:
        bool: True if successful
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Directly adding look {look_number} to {json_file_path}")
    
    try:
        if not os.path.exists(json_file_path):
            logger.error(f"JSON file not found: {json_file_path}")
            return False
            
        # Add timestamp to images
        timestamp = datetime.now().isoformat()
        for image in images:
            if "timestamp" not in image:
                image["timestamp"] = timestamp
            if "type" not in image:
                # Default to front
                image["type"] = "front"
                # Check alt text
                alt_text = image.get("alt_text", "").lower()
                if "back" in alt_text:
                    image["type"] = "back"
                elif "detail" in alt_text:
                    image["type"] = "detail"
                    
        # Read current data
        with open(json_file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in file {json_file_path}")
                return False
            
        # Verify structure
        if "seasons" not in data or len(data["seasons"]) <= season_index:
            logger.error(f"Invalid season index: {season_index}")
            return False
            
        if "designers" not in data["seasons"][season_index] or len(data["seasons"][season_index]["designers"]) <= designer_index:
            logger.error(f"Invalid designer index: {designer_index}")
            return False
            
        # Get designer
        designer = data["seasons"][season_index]["designers"][designer_index]
        
        # Ensure looks array exists
        if "looks" not in designer:
            designer["looks"] = []
            
        # Check if look exists
        look_exists = False
        for look in designer["looks"]:
            if str(look.get("look_number")) == str(look_number):
                look_exists = True
                # Add images to existing look
                if "images" not in look:
                    look["images"] = []
                look["images"].extend(images)
                look["completed"] = True
                break
                
        # Create new look if it doesn't exist
        if not look_exists:
            designer["looks"].append({
                "look_number": look_number,
                "images": images,
                "completed": True
            })
            
        # Update designer stats
        designer["extracted_looks"] = sum(1 for look in designer.get("looks", []) if look.get("completed", False))
        if designer.get("total_looks", 0) > 0 and designer["extracted_looks"] >= designer.get("total_looks", 0):
            designer["completed"] = True
            
        # Update metadata
        data["metadata"]["last_updated"] = timestamp
            
        # Write updated data - simplified with direct approach
        try:
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                
            # Verify file was written
            if not os.path.exists(json_file_path):
                logger.error(f"File disappeared after write: {json_file_path}")
                return False
                
            logger.info(f"Successfully added look {look_number} to {json_file_path}")
            print(f"Added look {look_number} with {len(images)} images to JSON")
            return True
            
        except Exception as write_error:
            logger.error(f"Error writing file: {str(write_error)}")
            return False
        
    except Exception as e:
        logger.error(f"Error directly adding look: {str(e)}")
        return False


def update_season_metadata(data: Dict[str, Any], season_index: int) -> None:
    """Update season metadata based on designer completion status.
    
    Args:
        data: Complete data structure
        season_index: Index of the season to update
    """
    try:
        if "seasons" not in data or season_index >= len(data["seasons"]):
            return
            
        season = data["seasons"][season_index]
        designers = season.get("designers", [])
        
        # Calculate completion statistics
        completed_designers = sum(1 for d in designers if d.get("completed", False))
        
        # Update season metadata
        season["completed_designers"] = completed_designers
        season["total_designers"] = len(designers)
        season["completed"] = completed_designers >= len(designers)
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error updating season metadata: {str(e)}")


def update_designer_completion(data: Dict[str, Any], season_index: int, designer_index: int) -> None:
    """Update designer completion status based on looks.
    
    Args:
        data: Complete data structure
        season_index: Index of the season
        designer_index: Index of the designer
    """
    try:
        if "seasons" not in data or season_index >= len(data["seasons"]):
            return
            
        season = data["seasons"][season_index]
        if "designers" not in season or designer_index >= len(season["designers"]):
            return
            
        designer = season["designers"][designer_index]
        
        # Count completed looks
        completed_looks = sum(1 for look in designer.get("looks", []) 
                              if look.get("completed", False) and look.get("images"))
        
        # Update designer metadata
        designer["extracted_looks"] = completed_looks
        
        # Calculate completion status
        total_looks = designer.get("total_looks", 0)
        if total_looks > 0:
            designer["completed"] = completed_looks >= total_looks
        else:
            designer["completed"] = False
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error updating designer completion: {str(e)}")


def update_global_progress(data: Dict[str, Any]) -> None:
    """Update global progress statistics in metadata.
    
    Args:
        data: Complete data structure
    """
    try:
        if "metadata" not in data:
            data["metadata"] = {}
        
        if "overall_progress" not in data["metadata"]:
            data["metadata"]["overall_progress"] = {}
            
        progress = data["metadata"]["overall_progress"]
        
        # Calculate global stats
        total_seasons = len(data.get("seasons", []))
        completed_seasons = 0
        total_designers = 0
        completed_designers = 0
        total_looks = 0
        extracted_looks = 0
        
        # Count from all seasons
        for season in data.get("seasons", []):
            if season.get("completed", False):
                completed_seasons += 1
                
            # Count designers
            designers = season.get("designers", [])
            total_designers += len(designers)
            
            for designer in designers:
                if designer.get("completed", False):
                    completed_designers += 1
                    
                # Count looks
                total_looks += designer.get("total_looks", 0)
                extracted_looks += designer.get("extracted_looks", 0)
        
        # Update progress metadata
        progress.update({
            "total_seasons": total_seasons,
            "completed_seasons": completed_seasons,
            "total_designers": total_designers,
            "completed_designers": completed_designers,
            "total_looks": total_looks,
            "extracted_looks": extracted_looks,
            "last_updated": datetime.now().isoformat()
        })
        
        # Calculate completion percentage
        if total_looks > 0:
            progress["completion_percentage"] = round((extracted_looks / total_looks) * 100, 2)
            
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error updating global progress: {str(e)}")