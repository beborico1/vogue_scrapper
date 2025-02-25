# utils/storage/utils.py
"""Utility functions for data storage operations.

This module provides utility functions for common storage operations,
including file generation, data type determination, and file operations.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

from src.exceptions.errors import FileOperationError
from src.config.settings import STORAGE, config


def generate_filename(base_dir: Union[str, Path], prefix: Optional[str] = None) -> Path:
    """Generate a filename with timestamp for data storage.

    Args:
        base_dir: Base directory for storing files
        prefix: Optional prefix for the filename (defaults to config setting)

    Returns:
        Path: Generated file path with timestamp

    Example:
        >>> generate_filename('data')
        Path('data/vogue_runway_20240121_123456.json')
    """
    timestamp = datetime.now().strftime(STORAGE["timestamp_format"])
    file_prefix = prefix or STORAGE["file_prefix"]
    return Path(base_dir) / f"{file_prefix}_{timestamp}.json"


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


def read_json_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Read and parse a JSON file.

    Args:
        file_path: Path to the JSON file

    Returns:
        Dict[str, Any]: Parsed JSON data

    Raises:
        FileOperationError: If file cannot be read or parsed

    Example:
        >>> data = read_json_file('data/storage.json')
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        raise FileOperationError(f"Error reading JSON file {file_path}: {str(e)}")


def write_json_file(file_path: Union[str, Path], data: Dict[str, Any]) -> None:
    """Write data to a JSON file with proper formatting.

    Args:
        file_path: Path where to write the JSON file
        data: Data to write to the file

    Raises:
        FileOperationError: If file cannot be written

    Example:
        >>> write_json_file('data/storage.json', {'key': 'value'})
    """
    try:
        # Simple direct write approach for reliability
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            # Force flush to disk
            f.flush()
            
        # Simple verification
        print(f"JSON file written: {file_path}")
    except Exception as e:
        error_msg = f"Error writing JSON file {file_path}: {str(e)}"
        print(f"ERROR: {error_msg}")
        raise FileOperationError(error_msg)
        
        
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
    import os
    import logging
    
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


def ensure_directory_exists(directory: Union[str, Path]) -> None:
    """Create a directory if it doesn't exist.

    Args:
        directory: Directory path to create

    Raises:
        FileOperationError: If directory cannot be created

    Example:
        >>> ensure_directory_exists('data/images')
    """
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise FileOperationError(f"Error creating directory {directory}: {str(e)}")


def validate_file_path(
    file_path: Union[str, Path], base_dir: Optional[Union[str, Path]] = None
) -> Path:
    """Validate and normalize a file path.

    Args:
        file_path: File path to validate
        base_dir: Optional base directory for relative paths

    Returns:
        Path: Normalized absolute path

    Raises:
        FileOperationError: If path is invalid or inaccessible

    Example:
        >>> path = validate_file_path('storage.json', 'data')
    """
    try:
        path = Path(file_path)
        if not path.is_absolute() and base_dir:
            path = Path(base_dir) / path
        return path.resolve()
    except Exception as e:
        raise FileOperationError(f"Invalid file path {file_path}: {str(e)}")


def get_file_info(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Get information about a file.

    Args:
        file_path: Path to the file

    Returns:
        Dict[str, Any]: File information including size, modification time, etc.

    Raises:
        FileOperationError: If file information cannot be retrieved

    Example:
        >>> info = get_file_info('data/storage.json')
        >>> print(info['size_mb'])
    """
    try:
        path = Path(file_path)
        stats = path.stat()
        return {
            "size_bytes": stats.st_size,
            "size_mb": round(stats.st_size / (1024 * 1024), 2),
            "modified": datetime.fromtimestamp(stats.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(stats.st_ctime).isoformat(),
            "is_file": path.is_file(),
            "extension": path.suffix,
            "name": path.name,
        }
    except Exception as e:
        raise FileOperationError(f"Error getting file info for {file_path}: {str(e)}")


def cleanup_old_files(
    directory: Union[str, Path], pattern: str = "*.json", max_files: int = 5
) -> None:
    """Clean up old files in a directory, keeping only the most recent ones.

    Args:
        directory: Directory to clean
        pattern: File pattern to match
        max_files: Maximum number of files to keep

    Raises:
        FileOperationError: If cleanup operation fails

    Example:
        >>> cleanup_old_files('data', '*.json', 3)
    """
    try:
        path = Path(directory)
        files = sorted(path.glob(pattern), key=lambda x: x.stat().st_mtime, reverse=True)

        for file in files[max_files:]:
            try:
                file.unlink()
            except Exception as e:
                raise FileOperationError(f"Error deleting file {file}: {str(e)}")
    except Exception as e:
        raise FileOperationError(f"Error during cleanup of {directory}: {str(e)}")


def merge_json_files(files: list[Union[str, Path]], output_file: Union[str, Path]) -> None:
    """Merge multiple JSON files into one.

    Args:
        files: List of files to merge
        output_file: Path for the merged output file

    Raises:
        FileOperationError: If merge operation fails

    Example:
        >>> merge_json_files(['data1.json', 'data2.json'], 'merged.json')
    """
    try:
        merged_data = {
            "metadata": {
                "merged_at": datetime.now().isoformat(),
                "source_files": [str(f) for f in files],
            },
            "seasons": [],
        }

        for file in files:
            data = read_json_file(file)
            if "seasons" in data:
                merged_data["seasons"].extend(data["seasons"])

        write_json_file(output_file, merged_data)
    except Exception as e:
        raise FileOperationError(f"Error merging JSON files: {str(e)}")
