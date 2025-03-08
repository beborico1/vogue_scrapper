# src/parallel/parallel_look_processor_worker.py
"""
Worker methods for processing individual looks in parallel.

This module contains functions for processing individual looks and extracting
image data using separate threads.
"""

import threading
import traceback
from typing import Dict, List, Any, Optional
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.remote.webdriver import WebDriver

from src.utils.driver import setup_chrome_driver
from src.utils.wait_utils import wait_for_page_load, wait_for_element_presence


def process_single_look(
    look_url: str, 
    look_number: int, 
    season_index: int, 
    designer_index: int,
    logger,
    storage) -> Dict[str, Any]:
    """
    Process a single look using its URL.
    
    Args:
        look_url: URL of the look
        look_number: Number of the look
        season_index: Index of the season
        designer_index: Index of the designer
        logger: Logger instance
        storage: Storage handler instance
        
    Returns:
        Dict containing processing results
    """
    result = {"look_number": look_number, "success": False}
    thread_id = threading.get_ident()
    
    try:
        logger.info(f"[Thread {thread_id}] Processing look {look_number}: {look_url}")
        
        # Create a new driver for this thread
        thread_driver = setup_chrome_driver()
        
        try:
            # Navigate directly to the look's URL
            thread_driver.get(look_url)
            
            # Wait for page to load
            wait_for_page_load(thread_driver)
            
            # Extract images for the look
            images = extract_look_images(thread_driver, look_number, logger)
            
            if not images:
                logger.warning(f"[Thread {thread_id}] No images found for look {look_number}")
                result["success"] = False
                return result
            
            # Store the images
            success = store_look_data(
                season_index, 
                designer_index, 
                look_number, 
                images,
                storage,
                logger
            )
            
            if success:
                logger.info(f"[Thread {thread_id}] Successfully processed look {look_number}")
                result["success"] = True
            else:
                logger.error(f"[Thread {thread_id}] Failed to store data for look {look_number}")
            
            return result
            
        finally:
            # Always close the thread's driver
            thread_driver.quit()
            
    except Exception as e:
        logger.error(f"[Thread {thread_id}] Error processing look {look_number}: {str(e)}")
        traceback.print_exc()
        return result


def extract_look_images(
    thread_driver: WebDriver, 
    look_number: int,
    logger
) -> List[Dict[str, str]]:
    """
    Extract all images for a given look using a dedicated driver.
    
    Args:
        thread_driver: WebDriver instance for this thread
        look_number: Number of the look to extract
        logger: Logger instance
        
    Returns:
        List of image data dictionaries
    """
    try:
        # Find the image collection container
        collection = wait_for_element_presence(
            thread_driver, 
            (By.CLASS_NAME, "RunwayGalleryImageCollection"),
            10
        )
        
        if not collection:
            logger.error(f"Image collection not found for look {look_number}")
            return []
        
        # Find all image elements
        image_elements = collection.find_elements(
            By.CLASS_NAME, "ImageCollectionListItem-YjTJj"
        )
        
        images = []
        for img_elem in image_elements:
            # Scroll to ensure the image is loaded
            thread_driver.execute_script("arguments[0].scrollIntoView(true);", img_elem)
            
            # Extract image data
            image_data = extract_single_image(thread_driver, img_elem, look_number, logger)
            if image_data:
                images.append(image_data)
        
        return images
        
    except Exception as e:
        logger.error(f"Error extracting images for look {look_number}: {str(e)}")
        return []


def extract_single_image(
    thread_driver: WebDriver, 
    img_elem, 
    look_number: int,
    logger
) -> Optional[Dict[str, str]]:
    """
    Extract data for a single image.
    
    Args:
        thread_driver: WebDriver instance for this thread
        img_elem: Image element
        look_number: Number of the look
        logger: Logger instance
        
    Returns:
        Optional dictionary with image data or None if extraction failed
    """
    try:
        img = img_elem.find_element(By.CLASS_NAME, "ResponsiveImageContainer-eybHBd")
        
        if not img:
            return None
        
        img_url = img.get_attribute("src")
        if not img_url or "/verso/static/" in img_url:
            return None
        
        # Ensure we're getting the high-res version
        if "assets.vogue.com" in img_url:
            img_url = img_url.replace("w_320", "w_1920")
            
            alt_text = img.get_attribute("alt") or f"Look {look_number}"
            
            # Determine image type based on alt text
            img_type = "front"  # Default type
            alt_lower = alt_text.lower()
            if "back" in alt_lower:
                img_type = "back"
            elif "detail" in alt_lower:
                img_type = "detail"
            
            # Include all required fields for the look storage
            return {
                "url": img_url,
                "look_number": str(look_number),
                "alt_text": alt_text,
                "type": img_type,
                "timestamp": datetime.now().isoformat()
            }
        
        return None
        
    except NoSuchElementException:
        return None
    except Exception as e:
        logger.error(f"Error extracting single image: {str(e)}")
        return None


def store_look_data(
    season_index: int, 
    designer_index: int, 
    look_number: int, 
    images: List[Dict[str, str]],
    storage,
    logger
) -> bool:
    """
    Store the extracted look data.
    
    Args:
        season_index: Index of the season
        designer_index: Index of the designer
        look_number: Number of the look
        images: List of image data dictionaries
        storage: Storage handler instance
        logger: Logger instance
        
    Returns:
        bool: True if storage was successful
    """
    try:
        # Call the storage handler to update look data
        return storage.update_look_data(
            season_index=season_index,
            designer_index=designer_index,
            look_number=look_number,
            images=images
        )
    except Exception as e:
        logger.error(f"Error storing look {look_number} data: {str(e)}")
        return False