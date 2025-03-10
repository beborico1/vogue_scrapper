# Vogue Runway Scraper

A robust web scraping tool designed to collect and store fashion runway data from Vogue Runway with real-time storage capabilities and checkpoint resumption.

## Features

- Real-time data storage with checkpoint resumption
- Automated authentication handling
- Season-by-season runway collection
- Designer-specific data gathering
- Runway image processing
- Robust error handling and logging
- Progress tracking and resumable operations

## Prerequisites

- Python 3.x
- Chrome/Chromium browser
- Chrome WebDriver

## Installation

1. Clone the repository:

    ```bash
    git clone <repository-url>
    cd voguescrapper
    ```

2. Install required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

3. Configure Chrome WebDriver:
   - Ensure Chrome/Chromium is installed
   - Download the appropriate version of ChromeDriver
   - Add ChromeDriver to your system PATH

## Project Structure

```structure
.
├── README.md
├── main.py
├── requirements.txt
├── data
│   └── vogue_runway_[timestamp].json
├── logs
│   └── vogue_scraper_[timestamp].log
└── src
    ├── config
    │   └── settings.py
    ├── exceptions
    │   └── errors.py
    ├── handlers
    │   ├── auth.py
    │   ├── designers.py
    │   ├── seasons.py
    │   ├── shows.py
    │   └── images
    │       ├── gallery_handler.py
    │       ├── image_extractor.py
    │       ├── images_handler.py
    │       ├── look_tracker.py
    │       └── slideshow_navigator.py
    ├── scraper.py
    └── utils
        ├── driver.py
        ├── logging.py
        └── storage
            ├── base_handler.py
            ├── data_updater.py
            ├── models.py
            ├── progress_tracker.py
            ├── storage_handler.py
            └── utils.py
```

## Usage

### Basic Run

To start a new scraping session:

```bash
python main.py
```

### Resume from Checkpoint

To resume scraping from a previous checkpoint:

```bash
python main.py --checkpoint vogue_data_[timestamp].json
```

Example:

```bash
python main.py --checkpoint vogue_data_20250120_191830.json
```

### Using Redis Storage

To use Redis as the storage backend:

```bash
python main.py --storage redis
```

You can also specify Redis connection parameters:

```bash
python main.py --storage redis --redis-host localhost --redis-port 6379 --redis-db 0
```

To resume from a Redis checkpoint:

```bash
python main.py --storage redis --checkpoint 20250120_191830
```

The scraper will:

1. Initialize storage or load existing checkpoint
2. Set up the Chrome WebDriver
3. Authenticate with Vogue Runway
4. Begin collecting data season by season
5. Store data in real-time with progress tracking

## Data Storage

The scraper supports two storage backends:

### JSON Storage (Default)

Data is stored in JSON format in the `data` directory with timestamp-based filenames:

- Filename format: `vogue_data_YYYYMMDD_HHMMSS.json`
- Example: `vogue_data_20250120_191830.json`

The JSON structure follows:

```json
{
  "metadata": {
    "created_at": "2025-01-20T19:18:30.123456",
    "last_updated": "2025-01-20T20:45:12.654321",
    "overall_progress": {
      "total_seasons": 10,
      "completed_seasons": 5,
      "total_designers": 150,
      "completed_designers": 75,
      "total_looks": 3000,
      "extracted_looks": 1500
    }
  },
  "seasons": [
    {
      "season": "Spring",
      "year": "2025",
      "url": "season_url",
      "designers": [
        {
          "name": "Designer Name",
          "url": "designer_url",
          "slideshow_url": "slideshow_url",
          "total_looks": 45
        }
      ]
    }
  ]
}
```

### Redis Storage

For improved performance and reliability, the scraper also supports Redis as a storage backend:

- Data is stored in Redis with structured keys
- Checkpoint IDs are timestamp-based: `20250120_191830`
- Supports real-time querying and monitoring
- Better handles concurrent operations

Redis keys follow these patterns:
- `vogue:metadata` - Overall metadata
- `vogue:seasons` - Set of all season identifiers
- `vogue:designers` - Set of all designer identifiers
- `vogue:season:{season}:{year}` - Season data
- `vogue:designer:{url}` - Designer data
- `vogue:look:{designer_url}:{look_number}` - Look data

## Logging

All operations are logged in the `logs` directory:

- Filename format: `vogue_scraper_YYYYMMDD_HHMMSS.log`
- Logs include:
  - Operation progress
  - Errors and warnings
  - Processing status
  - Checkpoint information

## Components

### Handlers

- `auth.py`: Authentication management
- `designers.py`: Designer data collection
- `seasons.py`: Season information processing
- `shows.py`: Fashion show data handling
- `images/`: Image processing components
  - `gallery_handler.py`: Gallery page processing
  - `image_extractor.py`: Image extraction utilities
  - `images_handler.py`: Main image processing
  - `look_tracker.py`: Look counting and tracking
  - `slideshow_navigator.py`: Slideshow navigation

### Utils

- `driver.py`: Chrome WebDriver setup and management
- `logging.py`: Logging configuration
- `storage/`: Data storage components
  - `base_handler.py`: Base storage functionality
  - `data_updater.py`: Data update operations
  - `progress_tracker.py`: Progress tracking
  - `storage_handler.py`: Main storage handling
  - `utils.py`: Storage utilities

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Vogue Runway for providing fashion runway content
- Selenium WebDriver for web automation capabilities
