# CLAUDE.md - Vogue Scraper Project Guidelines

## Commands
- Run scraper: `python main.py`
- Resume from checkpoint: `python main.py --checkpoint data/vogue_data_YYYYMMDD_HHMMSS.json`
- Install dependencies: `pip install -r requirements.txt`

## Code Style Guidelines
- **Imports**: Group standard library, third-party, and local imports
- **Types**: Use Python type hints (`from typing import Dict, Optional, List, Tuple, Any`)
- **Docstrings**: Use Google-style docstrings with Args/Returns sections
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Error handling**: Use try/except with specific exceptions
- **Folders**: Use modular organization with handlers, utils, config
- **Methods**: Keep methods focused on a single responsibility
- **Logging**: Use built-in logging utilities with appropriate levels
- **Storage**: Use real-time storage with checkpoint resumption

## Project Structure
The project follows a modular design with separate components for scraping, storage, and driver management. Handle errors with specific exception classes and appropriate logging.