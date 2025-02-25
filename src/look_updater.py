#!/usr/bin/env python3
"""
Emergency look updater script - saves look data directly to JSON file.
This is a minimal standalone script with no dependencies on the rest of the codebase.
"""

import json
import os
import sys
import time
from datetime import datetime


def emergency_add_look(json_path, season_idx, designer_idx, look_num, img_urls):
    """Ultra simple function to update JSON directly with minimal dependencies"""
    print(f"EMERGENCY LOOK UPDATE: s:{season_idx} d:{designer_idx} l:{look_num} imgs:{len(img_urls)}")
    
    if not os.path.exists(json_path):
        print(f"ERROR: JSON file not found: {json_path}")
        return False
        
    # Read file
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"ERROR reading JSON: {str(e)}")
        return False
        
    # Basic validation
    if not isinstance(data, dict) or "seasons" not in data:
        print("ERROR: Invalid JSON structure - no seasons")
        return False
        
    if season_idx >= len(data["seasons"]):
        print(f"ERROR: Season index {season_idx} out of bounds")
        return False
        
    season = data["seasons"][season_idx]
    if "designers" not in season or designer_idx >= len(season["designers"]):
        print(f"ERROR: Designer index {designer_idx} out of bounds")
        return False
        
    # Get designer
    designer = season["designers"][designer_idx]
    
    # Create looks array if needed
    if "looks" not in designer:
        designer["looks"] = []
    
    # Create image objects
    timestamp = datetime.now().isoformat()
    images = []
    for url in img_urls:
        images.append({
            "url": url,
            "look_number": str(look_num),
            "alt_text": f"Look {look_num}",
            "type": "front",
            "timestamp": timestamp
        })
    
    # Create or update look
    look_found = False
    for look in designer["looks"]:
        if str(look.get("look_number")) == str(look_num):
            look_found = True
            if "images" not in look:
                look["images"] = []
            look["images"].extend(images)
            look["completed"] = True
            break
            
    if not look_found:
        designer["looks"].append({
            "look_number": look_num,
            "images": images,
            "completed": True
        })
    
    # Update counts
    designer["extracted_looks"] = sum(1 for look in designer["looks"] if look.get("completed", False))
    
    # Write file as simply as possible
    try:
        # Direct write approach for maximum reliability
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)  # No fancy formatting, just write the JSON
            f.flush()
            os.fsync(f.fileno())  # Force the OS to flush to disk
        
        print(f"SUCCESS: Updated look {look_num} with {len(images)} images in {json_path}")
        return True
        
    except Exception as e:
        print(f"ERROR writing JSON: {str(e)}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python look_updater.py <json_path> <season_idx> <designer_idx> <look_num> <img_url1> [img_url2] ...")
        sys.exit(1)
        
    json_path = sys.argv[1]
    season_idx = int(sys.argv[2])
    designer_idx = int(sys.argv[3])
    look_num = int(sys.argv[4])
    img_urls = sys.argv[5:]
    
    if not img_urls:
        print("ERROR: At least one image URL is required")
        sys.exit(1)
        
    result = emergency_add_look(json_path, season_idx, designer_idx, look_num, img_urls)
    sys.exit(0 if result else 1)