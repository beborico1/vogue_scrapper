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
    
    # Make sure total_looks is set and at least as high as current look
    if "total_looks" not in designer or designer["total_looks"] < look_num:
        designer["total_looks"] = max(look_num, designer.get("total_looks", 0))
        print(f"Updated total_looks to {designer['total_looks']}")
    
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
    
    # Count and update extracted_looks
    completed_count = sum(1 for look in designer["looks"] if look.get("completed", False) and "images" in look and look["images"])
    designer["extracted_looks"] = completed_count
    
    # Log the extraction counts
    print(f"Extraction count for {designer.get('name', 'Unknown')}: {completed_count}/{designer.get('total_looks', 0)} completed looks")
    
    # Update completion status
    designer["completed"] = (designer["extracted_looks"] >= designer["total_looks"]) if designer.get("total_looks", 0) > 0 else False
    
    # Update season completion counts
    season["completed_designers"] = sum(1 for d in season["designers"] if d.get("completed", False))
    season["completed"] = (season["completed_designers"] >= len(season["designers"])) if len(season["designers"]) > 0 else False
    
    # Update metadata progress
    if "metadata" in data and "overall_progress" in data["metadata"]:
        progress = data["metadata"]["overall_progress"]
        
        # Count totals from all seasons/designers
        total_looks = 0
        extracted_looks = 0
        for s in data["seasons"]:
            for d in s.get("designers", []):
                total_looks += d.get("total_looks", 0)
                extracted_looks += d.get("extracted_looks", 0)
        
        # Update progress
        progress["total_looks"] = total_looks
        progress["extracted_looks"] = extracted_looks
        
        # Calculate completion percentage
        if total_looks > 0:
            progress["completion_percentage"] = round((extracted_looks / total_looks) * 100, 2)
        
        print(f"Updated progress: {extracted_looks}/{total_looks} looks ({progress.get('completion_percentage', 0)}%)")
    
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