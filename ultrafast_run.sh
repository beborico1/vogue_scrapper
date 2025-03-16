#!/bin/bash
# Simple wrapper script to run the ultrafast scraper

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Run the ultrafast scraper
"$SCRIPT_DIR/ultrafast/run.sh"