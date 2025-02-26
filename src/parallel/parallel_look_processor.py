"""
Look-level parallel processing for Vogue Runway scraper.

This module provides the main class for processing looks in parallel,
implementing a specialized scraper for parallel look extraction.
"""

import threading
import traceback
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import concurrent.futures

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.remote.webdriver import WebDriver

from src.utils.driver import setup_chrome_driver
from .parallel_look_processor_worker import process_single_look, extract_look_images


class ParallelLookScraper:
    """
    Specialized scraper for processing looks in parallel.
    
    This class extends the functionality of VogueSlideshowScraper to enable
    parallel processing of looks within a designer's collection.
    """
    
    def __init__(self, driver, logger, storage_handler, max_workers=4):
        """
        Initialize the parallel look scraper.
        
        Args:
            driver: WebDriver instance
            logger: Logger instance
            storage_handler: Storage handler instance
            max_workers: Maximum number of parallel workers for look processing
        """
        self.driver = driver
        self.logger = logger
        self.storage = storage_handler
        self.max_workers = max_workers
        
        # Create an instance of the regular scraper for navigation
        from src.handlers.slideshow.main_scrapper import VogueSlideshowScraper
        self.base_scraper = VogueSlideshowScraper(driver, logger, storage_handler)
    
    def scrape_designer_slideshow_parallel(self, 
                                          designer_url: str, 
                                          season_index: int, 
                                          designer_index: int,
                                          progress_tracker) -> Tuple[bool, Dict[str, Any]]:
        """
        Scrape all looks from a designer's slideshow in parallel.
        
        Args:
            designer_url: URL of the designer's page
            season_index: Index of the season
            designer_index: Index of the designer
            progress_tracker: Progress tracker instance
            
        Returns:
            Tuple of (success flag, processing statistics)
        """
        stats = {
            "total_looks": 0,
            "processed_looks": 0,
            "errors": []
        }
        
        try:
            self.logger.info(f"Starting parallel look scraping for {designer_url}")
            
            # Navigate to designer page and enter slideshow view
            if not self._navigate_to_slideshow(designer_url):
                error_msg = f"Failed to navigate to slideshow for {designer_url}"
                self.logger.error(error_msg)
                stats["errors"].append(error_msg)
                return False, stats
            
            # Get total number of looks
            total_looks = self._get_total_looks()
            if total_looks == 0:
                self.logger.error("No looks found in slideshow")
                return False, stats
            
            stats["total_looks"] = total_looks
            self.logger.info(f"Found {total_looks} looks to process in parallel")
            
            # Update total looks in storage
            current_data = self.storage.read_data()
            season = current_data["seasons"][season_index]
            designer = season["designers"][designer_index]
            designer["total_looks"] = total_looks
            self.storage.write_data(current_data)
            
            # First navigate through all looks to collect their URLs
            self.logger.info("Pre-scanning all looks to collect URLs")
            look_urls = self._scan_all_look_urls(total_looks)
            
            if len(look_urls) < total_looks:
                self.logger.warning(f"Only found {len(look_urls)} URLs out of {total_looks} looks")
            
            # Process looks in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(self.max_workers, len(look_urls))) as executor:
                # Submit tasks for each look
                look_tasks = {}
                for look_number, look_url in look_urls.items():
                    look_tasks[executor.submit(
                        process_single_look,
                        look_url,
                        look_number,
                        season_index,
                        designer_index,
                        self.logger,
                        self.storage
                    )] = look_number
                
                # Collect results as they complete
                for future in concurrent.futures.as_completed(look_tasks):
                    look_number = look_tasks[future]
                    try:
                        look_result = future.result()
                        stats["processed_looks"] += 1
                        
                        # Update progress
                        progress_tracker.update_look_progress(season_index, designer_index)
                        
                        # Log progress summary every 5 looks
                        if stats["processed_looks"] % 5 == 0:
                            self.logger.info(f"Processing progress: {stats['processed_looks']}/{total_looks} looks")
                            
                    except Exception as e:
                        error_msg = f"Error processing look {look_number}: {str(e)}"
                        self.logger.error(error_msg)
                        stats["errors"].append(error_msg)
            
            # Final progress update
            progress_tracker.update_progress(force_save=True)
            
            # Log results
            self.logger.info(f"Parallel look processing complete: {stats['processed_looks']}/{total_looks} looks processed")
            success = stats["processed_looks"] == total_looks
            
            return success, stats
            
        except Exception as e:
            error_msg = f"Error in parallel look scraping: {str(e)}"
            self.logger.error(error_msg)
            traceback.print_exc()
            stats["errors"].append(error_msg)
            return False, stats
    
    def _navigate_to_slideshow(self, designer_url: str) -> bool:
        """
        Navigate to the designer's slideshow.
        
        Args:
            designer_url: URL of the designer's page
            
        Returns:
            bool: True if navigation was successful
        """
        # Reuse the navigation method from the base scraper
        return self.base_scraper._navigate_to_slideshow(designer_url)
    
    def _get_total_looks(self) -> int:
        """
        Get the total number of looks in the slideshow.
        
        Returns:
            int: Total number of looks
        """
        # Reuse the total looks method from the base scraper
        return self.base_scraper._get_total_looks()
    
    def _scan_all_look_urls(self, total_looks: int) -> Dict[int, str]:
        """
        Scan through all looks to collect their URLs.
        
        This allows us to process looks in parallel without needing to navigate
        sequentially through the slideshow for each look.
        
        Args:
            total_looks: Total number of looks to scan
            
        Returns:
            Dict mapping look numbers to their URLs
        """
        look_urls = {}
        current_look = 1
        
        try:
            # Reset to first look
            self.driver.get(self.driver.current_url.split("#")[0] + "#1")
            time.sleep(2)
            
            while current_look <= total_looks:
                # Get current URL with fragment identifier
                current_url = self.driver.current_url
                look_urls[current_look] = current_url
                
                self.logger.info(f"Collected URL for look {current_look}: {current_url}")
                
                if current_look < total_looks:
                    # Navigate to next look
                    if not self._navigate_to_next_look():
                        self.logger.error(f"Failed to navigate to next look after {current_look}")
                        break
                
                current_look += 1
            
            return look_urls
            
        except Exception as e:
            self.logger.error(f"Error scanning look URLs: {str(e)}")
            return look_urls
    
    def _navigate_to_next_look(self) -> bool:
        """
        Navigate to the next look in the slideshow.
        
        Returns:
            bool: True if navigation was successful
        """
        # Reuse the navigation method from the base scraper
        return self.base_scraper._navigate_to_next_look()