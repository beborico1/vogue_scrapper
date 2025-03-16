#!/bin/bash
# Run script for Ultrafast Vogue Scraper

# Set Redis configuration
REDIS_HOST="localhost"
REDIS_PORT="6379"
REDIS_DB="0"
REDIS_PASSWORD=""  # Leave empty if no password

# Set number of parallel workers
WORKERS=6  # Increased as we have better cookie sharing now

# Set command line options
USE_STATIC_SEASONS="--use-static-seasons"
SEQUENTIAL=""  # Leave empty to use parallel processing (better now with cookie sharing)
RESUME=""  # Use "--resume" to resume from previous session

# Uncomment line below to use sequential processing instead of parallel
# SEQUENTIAL="--sequential"

# Determine script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Check if data directory exists
if [ ! -d "$SCRIPT_DIR/data" ]; then
    mkdir -p "$SCRIPT_DIR/data"
    echo "Created data directory"
fi

# Run the scraper
cd "$PROJECT_DIR"
python -m ultrafast.main \
    --redis-host $REDIS_HOST \
    --redis-port $REDIS_PORT \
    --redis-db $REDIS_DB \
    --workers $WORKERS \
    $USE_STATIC_SEASONS \
    $SEQUENTIAL \
    $RESUME

echo "Ultrafast Vogue Scraper completed"