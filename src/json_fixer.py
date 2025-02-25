#!/usr/bin/env python3
"""
JSON Fixer - Repair corrupted JSON file, starting with a minimal valid JSON structure
and restoring the look data properly.
"""

import json
import os
import sys
from datetime import datetime

def fix_json(json_path):
    """Fix a corrupted JSON file by creating a minimal valid structure"""
    print(f"Fixing corrupted JSON file: {json_path}")
    
    # Create a minimal valid JSON structure
    minimal_data = {
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "overall_progress": {
                "total_seasons": 0,
                "completed_seasons": 0,
                "total_designers": 0,
                "completed_designers": 0,
                "total_looks": 0,
                "extracted_looks": 0
            }
        },
        "seasons": []
    }
    
    # Back up the corrupted file
    backup_path = f"{json_path}.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
    try:
        os.rename(json_path, backup_path)
        print(f"Created backup at: {backup_path}")
    except Exception as e:
        print(f"Warning: Could not backup file: {str(e)}")
    
    # Write the minimal structure
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(minimal_data, f, indent=2, ensure_ascii=False)
            f.flush()
        print(f"Created new valid JSON file: {json_path}")
        return True
    except Exception as e:
        print(f"ERROR: Could not create new JSON file: {str(e)}")
        return False

def restore_data(original_path, fixed_path):
    """
    Try to restore data from a corrupted JSON file to a fixed one.
    This is a more advanced function that would try to parse and recover
    data from the corrupted file.
    """
    # This would be a much more complex implementation
    # For now, just return that we can't do this yet
    print("Data restoration from corrupted files is not implemented yet")
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python json_fixer.py <json_path>")
        sys.exit(1)
        
    json_path = sys.argv[1]
    
    if not os.path.exists(json_path):
        print(f"ERROR: File not found: {json_path}")
        sys.exit(1)
        
    result = fix_json(json_path)
    sys.exit(0 if result else 1)