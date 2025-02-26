# utils/storage/utils.py
"""Utility functions for data storage operations.

This module serves as a front-end for utility functions that have been
split into specialized modules for maintainability.
"""

# Reexport all utilities from specialized modules
from .file_utils import (
    generate_filename,
    read_json_file,
    write_json_file,
    ensure_directory_exists,
    validate_file_path,
    get_file_info,
    cleanup_old_files,
    merge_json_files
)

from .data_utils import (
    determine_image_type,
    directly_add_look,
    update_season_metadata,
    update_designer_completion,
    update_global_progress
)

__all__ = [
    # File operations
    'generate_filename',
    'read_json_file',
    'write_json_file',
    'ensure_directory_exists',
    'validate_file_path',
    'get_file_info',
    'cleanup_old_files',
    'merge_json_files',
    
    # Data operations
    'determine_image_type',
    'directly_add_look',
    'update_season_metadata',
    'update_designer_completion',
    'update_global_progress'
]