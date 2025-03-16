#!/usr/bin/env python
"""
Static season extractor for Vogue Ultrafast Scraper.

This script generates a list of season URLs for Vogue's runway shows
based on a pattern without requiring network access.
"""

import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for shared imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def generate_season_urls(start_year=1980, end_year=None):
    """
    Generate season URLs based on known patterns.
    
    Args:
        start_year: Year to start generating seasons from (default: 1980)
        end_year: Year to end generating seasons at (default: current year + 1)
        
    Returns:
        List of season dictionaries with season, year, and URL
    """
    base_url = "https://www.vogue.com/fashion-shows"
    seasons = []
    
    # Get current year
    current_year = datetime.now().year
    
    # If end_year not provided, use current year + 1
    if end_year is None:
        end_year = current_year + 1
    
    # Define season patterns including historical naming conventions
    season_patterns = [
        # Standard ready-to-wear seasons (all years)
        {"name": "Spring Ready-to-Wear", "url_part": "spring-{year}-ready-to-wear"},
        {"name": "Fall Ready-to-Wear", "url_part": "fall-{year}-ready-to-wear"},
        
        # Resort/Cruise collections (more common after 2000)
        {"name": "Resort", "url_part": "resort-{year}"},
        {"name": "Cruise", "url_part": "cruise-{year}"},
        
        # Pre-Fall (more common after 2000)
        {"name": "Pre-Fall", "url_part": "pre-fall-{year}"},
        
        # Couture collections
        {"name": "Spring Couture", "url_part": "spring-{year}-couture"},
        {"name": "Fall Couture", "url_part": "fall-{year}-couture"},
        
        # Menswear collections (more common after 2000)
        {"name": "Spring Menswear", "url_part": "spring-{year}-menswear"},
        {"name": "Fall Menswear", "url_part": "fall-{year}-menswear"},
        
        # Bridal collections (more common after 2000)
        {"name": "Bridal Spring", "url_part": "bridal-spring-{year}"},
        {"name": "Bridal Fall", "url_part": "bridal-fall-{year}"},
        
        # Historical naming conventions (primarily before 2010)
        {"name": "Spring RTW", "url_part": "spring-rtw-{year}"},
        {"name": "Fall RTW", "url_part": "fall-rtw-{year}"},
        {"name": "Spring/Summer", "url_part": "spring-summer-{year}"},
        {"name": "Fall/Winter", "url_part": "fall-winter-{year}"},
        {"name": "Haute Couture Spring", "url_part": "haute-couture-spring-{year}"},
        {"name": "Haute Couture Fall", "url_part": "haute-couture-fall-{year}"},
        
        # Other historical variations
        {"name": "S/S Ready-to-Wear", "url_part": "ss-{year}-ready-to-wear"},
        {"name": "F/W Ready-to-Wear", "url_part": "fw-{year}-ready-to-wear"},
        {"name": "S/S RTW", "url_part": "ss-{year}-rtw"},
        {"name": "F/W RTW", "url_part": "fw-{year}-rtw"},
    ]
    
    # Generate URLs for each year and season pattern
    for year in range(end_year, start_year - 1, -1):  # Newest first
        # Adjust patterns based on the era
        if year < 2000:
            # For older years, prioritize historical patterns
            era_patterns = [p for p in season_patterns if "RTW" in p["name"] or "Summer" in p["name"] or "Winter" in p["name"] or "Haute" in p["name"]]
            # Include other patterns as well
            era_patterns.extend([p for p in season_patterns if p not in era_patterns])
        else:
            # For recent years, use all patterns
            era_patterns = season_patterns
            
        for pattern in era_patterns:
            season_name = pattern["name"]
            url_part = pattern["url_part"].format(year=year)
            url = f"{base_url}/{url_part}"
            
            # Skip certain combinations that are unlikely to exist
            # (e.g., no resort collections before 1990)
            if year < 1990 and any(x in pattern["name"] for x in ["Resort", "Cruise", "Bridal", "Pre-Fall"]):
                continue
                
            # Skip menswear before 1995
            if year < 1995 and "Menswear" in pattern["name"]:
                continue
            
            seasons.append({
                "season": season_name,
                "year": str(year),
                "url": url
            })
    
    return seasons

def write_seasons_to_file(seasons, filename):
    """
    Write season URLs to a text file.
    
    Args:
        seasons: List of season dictionaries
        filename: Output filename
    """
    # Create parent directory if it doesn't exist
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w') as f:
        for season in seasons:
            f.write(f"{season['url']}\n")
    
    print(f"Wrote {len(seasons)} season URLs to {filename}")

def write_seasons_to_json(seasons, filename):
    """
    Write season data to a JSON file.
    
    Args:
        seasons: List of season dictionaries
        filename: Output filename
    """
    import json
    
    # Create parent directory if it doesn't exist
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w') as f:
        json.dump(seasons, f, indent=2)
    
    print(f"Wrote {len(seasons)} season data entries to {filename}")

def get_data_dir():
    """Get the data directory path."""
    # Get ultrafast directory
    ultrafast_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(ultrafast_dir, "data")

if __name__ == "__main__":
    # Generate seasons from 1980 to current year + 1
    start_year = 1980  # Starting from 1980 to cover Vogue's digital archive
    end_year = datetime.now().year + 1     # Include next year's shows
    
    # Get data directory
    data_dir = get_data_dir()
    
    # Generate the seasons
    seasons = generate_season_urls(start_year, end_year)
    
    # Write to text file
    write_seasons_to_file(seasons, os.path.join(data_dir, "seasons.txt"))
    
    # Write to JSON file
    write_seasons_to_json(seasons, os.path.join(data_dir, "seasons.json"))
    
    print(f"Generated {len(seasons)} seasons from {start_year} to {end_year}")