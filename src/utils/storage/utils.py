# utils/storage/utils.py
"""Utility functions for data storage operations.

This module provides utility functions for common storage operations,
including file generation, data type determination, and file operations.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union

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
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        raise FileOperationError(f"Error writing JSON file {file_path}: {str(e)}")


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
