#!/usr/bin/env python3
"""
Data Initializer - Creates a new empty JSON file with proper structure
and adds a test season, designer, and look to verify everything works.
"""

import json
import os
import sys
from datetime import datetime

def initialize_data(file_path):
    """Create a new data file with basic structure and test data."""
    print(f"Creating new data file: {file_path}")
    
    # Create minimal structure
    data = {
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "overall_progress": {
                "total_seasons": 1,
                "completed_seasons": 0,
                "total_designers": 1,
                "completed_designers": 0,
                "total_looks": 1,
                "extracted_looks": 0
            }
        },
        "seasons": [
            {
                "season": "TEST SEASON",
                "year": "2025",
                "url": "https://www.vogue.com/fashion-shows/test-season",
                "completed": False,
                "total_designers": 1,
                "completed_designers": 0,
                "designers": [
                    {
                        "name": "Test Designer",
                        "url": "https://www.vogue.com/fashion-shows/test-season/test-designer",
                        "total_looks": 1,
                        "extracted_looks": 0,
                        "completed": False,
                        "looks": []
                    }
                ]
            }
        ]
    }
    
    # Write to file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
            
        print(f"Successfully created new data file: {file_path}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to create data file: {str(e)}")
        return False
        
def add_test_look(file_path):
    """Add a test look to verify writing works."""
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Add a test look
        test_look = {
            "look_number": 1,
            "completed": True,
            "images": [
                {
                    "url": "https://test.example.com/test.jpg",
                    "look_number": "1",
                    "alt_text": "Test Look 1",
                    "type": "front",
                    "timestamp": datetime.now().isoformat()
                }
            ]
        }
        
        # Add to first designer's looks
        data["seasons"][0]["designers"][0]["looks"].append(test_look)
        data["seasons"][0]["designers"][0]["extracted_looks"] = 1
        data["seasons"][0]["designers"][0]["completed"] = True
        data["seasons"][0]["completed_designers"] = 1
        data["seasons"][0]["completed"] = True
        data["metadata"]["overall_progress"]["extracted_looks"] = 1
        data["metadata"]["overall_progress"]["completed_designers"] = 1
        data["metadata"]["overall_progress"]["completed_seasons"] = 1
        
        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
            
        print(f"Successfully added test look to {file_path}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to add test look: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python data_initializer.py <file_path>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    
    # Check if file already exists
    if os.path.exists(file_path):
        print(f"Warning: File already exists: {file_path}")
        choice = input("Overwrite? (y/n): ")
        if choice.lower() != 'y':
            print("Aborting.")
            sys.exit(0)
    
    # Initialize file
    success = initialize_data(file_path)
    if not success:
        sys.exit(1)
        
    # Add test look
    success = add_test_look(file_path)
    sys.exit(0 if success else 1)