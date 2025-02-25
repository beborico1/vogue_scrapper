#!/usr/bin/env python3
"""
JSON Debugger - Simple tool to examine the structure of the JSON file
and check if looks are properly stored.
"""

import json
import sys
import os
from datetime import datetime

def debug_json(json_path, season_idx=None, designer_idx=None):
    """Examine the JSON file and report on its structure"""
    print(f"DEBUG: Examining {json_path} at {datetime.now().isoformat()}")
    
    if not os.path.exists(json_path):
        print(f"ERROR: File not found: {json_path}")
        return False
        
    # Get file stats
    stats = os.stat(json_path)
    print(f"File size: {stats.st_size} bytes")
    print(f"Last modified: {datetime.fromtimestamp(stats.st_mtime).isoformat()}")
    
    # Read the file
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"ERROR reading JSON: {str(e)}")
        return False
        
    # Basic structure check
    if "seasons" not in data:
        print("ERROR: No 'seasons' array in JSON")
        return False
        
    print(f"Total seasons: {len(data['seasons'])}")
    
    # If season index provided, check that season
    if season_idx is not None:
        if season_idx >= len(data["seasons"]):
            print(f"ERROR: Season index {season_idx} out of bounds")
            return False
            
        season = data["seasons"][season_idx]
        print(f"Season: {season.get('season', 'Unknown')} {season.get('year', 'Unknown')}")
        print(f"Total designers: {len(season.get('designers', []))}")
        
        # If designer index provided, check that designer
        if designer_idx is not None:
            if designer_idx >= len(season.get("designers", [])):
                print(f"ERROR: Designer index {designer_idx} out of bounds")
                return False
                
            designer = season["designers"][designer_idx]
            print(f"Designer: {designer.get('name', 'Unknown')}")
            print(f"Extracted looks: {designer.get('extracted_looks', 0)}")
            print(f"Total looks: {designer.get('total_looks', 0)}")
            
            # Check looks array
            looks = designer.get("looks", [])
            print(f"Looks array length: {len(looks)}")
            
            for i, look in enumerate(looks[:10]):  # Print first 10 looks
                print(f"Look {i+1}: number={look.get('look_number')}, " +
                      f"completed={look.get('completed')}, " +
                      f"images={len(look.get('images', []))}")
                
            if len(looks) > 10:
                print(f"... and {len(looks) - 10} more looks")
                
    return True

def add_test_look(json_path, season_idx, designer_idx):
    """Add a test look to the JSON file to verify writing works"""
    if not os.path.exists(json_path):
        print(f"ERROR: File not found: {json_path}")
        return False
        
    # Read the file
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"ERROR reading JSON: {str(e)}")
        return False
        
    # Verify structure
    if "seasons" not in data or season_idx >= len(data["seasons"]):
        print(f"ERROR: Invalid season index: {season_idx}")
        return False
        
    if "designers" not in data["seasons"][season_idx] or designer_idx >= len(data["seasons"][season_idx]["designers"]):
        print(f"ERROR: Invalid designer index: {designer_idx}")
        return False
        
    # Get designer
    designer = data["seasons"][season_idx]["designers"][designer_idx]
    
    # Ensure looks array exists
    if "looks" not in designer:
        designer["looks"] = []
        
    # Add a test look
    look_num = 999  # Test look number that won't conflict
    timestamp = datetime.now().isoformat()
    
    # Create test look
    test_look = {
        "look_number": look_num,
        "completed": True,
        "images": [
            {
                "url": "https://test.example.com/test.jpg",
                "look_number": str(look_num),
                "alt_text": f"Test Look {look_num}",
                "type": "front",
                "timestamp": timestamp
            }
        ]
    }
    
    # Add to looks array
    designer["looks"].append(test_look)
    
    # Update extracted_looks count
    designer["extracted_looks"] = len(designer["looks"])
    
    # Write back to file
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"SUCCESS: Added test look {look_num} to {json_path}")
        return True
    except Exception as e:
        print(f"ERROR writing JSON: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python json_debugger.py <json_path> [season_idx] [designer_idx]")
        print("Or: python json_debugger.py --test <json_path> <season_idx> <designer_idx>")
        sys.exit(1)
        
    # Check for test mode
    if sys.argv[1] == "--test" and len(sys.argv) >= 5:
        json_path = sys.argv[2]
        season_idx = int(sys.argv[3])
        designer_idx = int(sys.argv[4])
        result = add_test_look(json_path, season_idx, designer_idx)
        # Debug the file after the test
        if result:
            debug_json(json_path, season_idx, designer_idx)
        sys.exit(0 if result else 1)
    
    # Debug mode    
    json_path = sys.argv[1]
    season_idx = int(sys.argv[2]) if len(sys.argv) > 2 else None
    designer_idx = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    debug_json(json_path, season_idx, designer_idx)