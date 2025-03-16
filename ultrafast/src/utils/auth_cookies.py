"""
Cookie management utilities for authentication.

This module provides utilities for sharing cookies between browser sessions to
speed up authentication.
"""

import os
import json
import time
import pickle
import logging
from typing import Dict, List, Optional
import threading

# Thread-safe lock for cookie access
_cookie_lock = threading.Lock()

# Global variables for cookie management
_auth_cookies = None
_cookie_timestamp = 0
_cookie_refresh_interval = 10 * 60  # Refresh cookies every 10 minutes
_cookie_max_age = 60 * 60  # Consider cookies expired after 1 hour

def save_auth_cookies(driver, config):
    """
    Save authentication cookies from a browser session.
    
    Args:
        driver: Selenium WebDriver instance
        config: Configuration object with data directory
    
    Returns:
        True if cookies were saved, False otherwise
    """
    global _auth_cookies, _cookie_timestamp
    
    try:
        cookies = driver.get_cookies()
        if not cookies:
            return False
        
        # Update in-memory cookies
        with _cookie_lock:
            _auth_cookies = cookies
            _cookie_timestamp = time.time()
            
        # Save to file
        cookies_dir = os.path.join(config.data_dir, "cookies")
        os.makedirs(cookies_dir, exist_ok=True)
        
        cookie_file = os.path.join(cookies_dir, "auth_cookies.pkl")
        with open(cookie_file, "wb") as f:
            pickle.dump(cookies, f)
            
        return True
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Error saving auth cookies: {str(e)}")
        return False

def load_auth_cookies(config) -> Optional[List[Dict]]:
    """
    Load authentication cookies from memory or file.
    
    Args:
        config: Configuration object with data directory
        
    Returns:
        List of cookie dictionaries or None if not found
    """
    global _auth_cookies, _cookie_timestamp, _cookie_max_age
    
    current_time = time.time()
    
    # First try to get cookies from memory
    with _cookie_lock:
        if _auth_cookies:
            # Check if cookies are still valid
            cookie_age = current_time - _cookie_timestamp
            
            if cookie_age < _cookie_max_age:
                # Cookies are still valid
                return _auth_cookies
            else:
                # Cookies are too old
                logger = logging.getLogger(__name__)
                logger.info(f"Cookies expired (age: {cookie_age:.1f}s)")
    
    # Otherwise try to load from file
    try:
        cookie_file = os.path.join(config.data_dir, "cookies", "auth_cookies.pkl")
        if not os.path.exists(cookie_file):
            # No cookie file found
            return None
            
        # Check file age
        file_modify_time = os.path.getmtime(cookie_file)
        file_age = current_time - file_modify_time
        
        if file_age > _cookie_max_age:
            # File is too old
            logger = logging.getLogger(__name__)
            logger.info(f"Cookie file too old (age: {file_age:.1f}s)")
            return None
            
        # Load cookies from file
        with open(cookie_file, "rb") as f:
            cookies = pickle.load(f)
            
        # Update in-memory cookies
        with _cookie_lock:
            _auth_cookies = cookies
            _cookie_timestamp = current_time
            
        return cookies
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Error loading auth cookies: {str(e)}")
        return None

def apply_auth_cookies(driver, config) -> bool:
    """
    Apply authentication cookies to a browser session.
    
    Args:
        driver: Selenium WebDriver instance
        config: Configuration object with data directory
        
    Returns:
        True if cookies were applied, False otherwise
    """
    logger = logging.getLogger(__name__)
    cookies = load_auth_cookies(config)
    
    if not cookies:
        logger.info("No valid cookies found to apply")
        return False
        
    try:
        # Navigate to the domain first (required for setting cookies)
        driver.get(config.BASE_URL)
        
        # Small wait to ensure page is ready for cookies
        time.sleep(1)
        
        # Count successfully applied cookies
        success_count = 0
        error_count = 0
        
        # Add each cookie to the browser
        for cookie in cookies:
            try:
                # Skip cookies without name or value
                if not cookie.get('name') or not cookie.get('value'):
                    continue
                
                # Clean up cookie for Chrome's requirements
                # Remove the problematic attributes that might cause issues
                clean_cookie = {k: v for k, v in cookie.items() 
                              if k in ['name', 'value', 'domain', 'path', 'secure', 'expiry']}
                
                # Apply the cookie
                driver.add_cookie(clean_cookie)
                success_count += 1
                
            except Exception as e:
                error_count += 1
                # Just count errors, don't break the process
                
        logger.info(f"Applied {success_count} cookies successfully ({error_count} errors)")
                
        # Refresh the page to activate cookies
        driver.refresh()
        
        return success_count > 0
        
    except Exception as e:
        logger.warning(f"Error applying auth cookies: {str(e)}")
        return False