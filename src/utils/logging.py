"""
Logging configuration and setup utilities.
"""

import logging
from datetime import datetime


def setup_logger():
    """
    Configure and initialize logging with custom format and file output.
    
    Returns:
        logging.Logger: Configured logger instance
    """
    log_filename = f'logs/vogue_scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    # Create logger
    logger = logging.getLogger('vogue_scraper')
    logger.setLevel(logging.INFO)
    
    # Create file handler
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info("Logging setup complete")
    return logger