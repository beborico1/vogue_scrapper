# Ultrafast Vogue Scraper

An optimized implementation of the Vogue Runway scraper that directly processes collection pages to extract all types of images from multiple sections (Collection, Details, Beauty, Front Row, etc.).

## Features

- Non-headless browser mode for visual monitoring of the scraping process
- Compatible authentication with the main scraper
- Redis storage for high performance data handling
- Extracts all sections from collection pages by handling "Load More" buttons
- Stores the following data files:
  - `ultrafast/data/seasons.txt`: All season URLs
  - `ultrafast/data/collections.txt`: All collection URLs
- Parallel processing of collection pages

## Requirements

- Python 3.7+
- Redis server (for data storage)
- Chrome browser
- Dependencies from the main project

## Usage

```bash
# Basic usage
python ultrafast/main.py

# With Redis configuration
python ultrafast/main.py --redis-host localhost --redis-port 6379 --redis-db 0

# With parallel processing (adjust worker count)
python ultrafast/main.py --workers 8

# Use statically generated seasons (recommended for reliability)
python ultrafast/main.py --use-static-seasons

# Process collections sequentially (avoids authentication issues)
python ultrafast/main.py --sequential

# Resume from previously stored data
python ultrafast/main.py --resume

# Use the run script (simplest option - uses both static seasons and sequential mode)
./ultrafast/run.sh
```

## How It Works

The ultrafast scraper uses a different approach compared to the main scraper:

1. **Authentication**: Uses the same authentication mechanism as the main scraper
2. **Season Extraction**:
   - Can use statically generated season URLs (recommended) for reliability
   - Or dynamically extract season URLs from Vogue's fashion shows pages
3. **Collection Extraction**: For each season, extracts all designer collection URLs
4. **Look Extraction**:
   - Navigates directly to collection pages (not the slideshow view)
   - Authenticates each browser session (with cookie sharing for efficiency)
   - Scrolls down to load all content
   - Extracts coverage text if available
   - Finds and clicks all "Load More" buttons to expand content sections
   - Extracts images from all sections (Collection, Details, Beauty, etc.)
   - Processes images with proper organization by section
   - Can process collections sequentially or in parallel

5. **Storage**:
   - Uses Redis for high-performance data storage
   - Organizes data hierarchically: Seasons > Collections > Sections > Looks
   - Stores metadata for efficient retrieval and progress tracking

## Data Structure in Redis

The data is stored in Redis with the following structure:

- `ultrafast:seasons`: List of all season URLs
- `ultrafast:season:<index>`: Hash containing season data
- `ultrafast:collections:<season_url>`: List of collection URLs for a season
- `ultrafast:collection:<collection_url>`: Hash containing collection data
- `ultrafast:looks:<collection_url>:<section_name>`: List of look IDs for a section
- `ultrafast:looks:<collection_url>:<section_name>:<look_id>`: Hash with image data

## Advanced Configuration

You can adjust timing and selectors in `src/config/settings.py` to optimize for different network conditions or site changes.

## Troubleshooting

- **Authentication Issues**: If automatic authentication fails, the scraper will wait for manual login
- **"Load More" Button Detection**: If fewer than 3 "Load More" buttons are found, check the console for warnings
- **Performance Optimization**: Adjust the number of workers based on your system's capabilities