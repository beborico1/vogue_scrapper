"""
Authentication handler for the Ultrafast Vogue Scraper.

This module handles the authentication process with Vogue's website,
including handling redirects and verifying authenticated state.
"""

import logging
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from ..utils.auth_cookies import save_auth_cookies, apply_auth_cookies


class AuthHandler:
    """Handles authentication with Vogue's website."""
    
    def __init__(self, driver: WebDriver, config, logger=None):
        """
        Initialize the authentication handler.
        
        Args:
            driver: Selenium WebDriver instance
            config: Configuration object
            logger: Logger instance (optional)
        """
        self.driver = driver
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
    
    def authenticate(self) -> bool:
        """
        Handle the authentication process.
        
        Returns:
            True if authentication is successful, False otherwise
        """
        self.logger.info("Starting authentication process...")
        
        # First try to use existing cookies - this should be the primary method
        if self._authenticate_with_cookies():
            self.logger.info("Authentication successful using shared cookies")
            # Refresh cookies to keep them fresh for other sessions
            save_auth_cookies(self.driver, self.config)
            return True
        
        # If cookie authentication failed, it might be the first session or cookies expired
        self.logger.info("Cookie authentication failed, trying direct authentication")
        
        try:
            # Navigate to the authentication URL
            self.driver.get(self.config.AUTH_URL)
            self.logger.info(f"Navigating to auth URL: {self.config.AUTH_URL}")
            
            # Handle redirects
            if not self._handle_redirects():
                return False
            
            # Check for authentication completion
            if "vogue.com/auth/complete" in self.driver.current_url:
                self.logger.info("Authentication successful - Found completion URL")
                # Save cookies for other sessions (this is critical!)
                save_auth_cookies(self.driver, self.config)
                return True
            
            # Check for login form and handle manual authentication
            if "id.condenast.com" in self.driver.current_url:
                self.logger.warning("Manual login required - Please sign in")
                
                # Wait for manual authentication (user needs to sign in)
                auth_timeout = 300  # 5 minutes max to log in manually
                start_time = time.time()
                
                while time.time() - start_time < auth_timeout:
                    # Check if we've reached the authenticated state
                    if self._check_authentication():
                        self.logger.info("Manual authentication completed successfully")
                        # Save cookies for other sessions
                        save_auth_cookies(self.driver, self.config)
                        return True
                    
                    # Check if we're at the completion URL
                    if "vogue.com/auth/complete" in self.driver.current_url:
                        self.logger.info("Authentication successful - Found completion URL")
                        # Save cookies for other sessions
                        save_auth_cookies(self.driver, self.config)
                        return True
                    
                    # Check if we're on the Vogue domain already
                    if "vogue.com" in self.driver.current_url:
                        self.logger.info("On Vogue domain, checking authentication")
                        if self.verify_authentication():
                            # Save cookies for other sessions
                            save_auth_cookies(self.driver, self.config)
                            return True
                    
                    # Wait a bit before checking again
                    time.sleep(2)
                
                self.logger.error("Authentication timed out waiting for manual sign-in")
                return False
            
            # Verify final authentication state
            authenticated = self.verify_authentication()
            if authenticated:
                # Save cookies for other sessions
                save_auth_cookies(self.driver, self.config)
            return authenticated
            
        except Exception as e:
            self.logger.error(f"Authentication error: {str(e)}")
            return False
    
    def _authenticate_with_cookies(self) -> bool:
        """
        Try to authenticate using saved cookies.
        
        Returns:
            True if authentication is successful, False otherwise
        """
        try:
            # Apply saved cookies
            if not apply_auth_cookies(self.driver, self.config):
                self.logger.info("No saved cookies found or error applying cookies")
                return False
            
            self.logger.info("Applied saved cookies, verifying authentication")
            
            # Navigate to Vogue to see if we're authenticated
            self.driver.get(self.config.BASE_URL)
            time.sleep(2)  # Short wait to let cookies take effect
            
            # Verify authentication
            return self.verify_authentication()
            
        except Exception as e:
            self.logger.warning(f"Error authenticating with cookies: {str(e)}")
            return False
    
    def _handle_redirects(self) -> bool:
        """
        Handle authentication redirects.
        
        Returns:
            True if redirects were handled successfully
        """
        max_redirects = 5
        redirect_count = 0
        last_url = self.driver.current_url
        
        # Wait for initial page load
        time.sleep(self.config.timing.PAGE_LOAD_WAIT)
        
        while redirect_count < max_redirects:
            try:
                # Check if URL has changed
                current_url = self.driver.current_url
                if current_url != last_url:
                    self.logger.info(f"Redirect {redirect_count + 1}: {current_url}")
                    last_url = current_url
                    redirect_count += 1
                    
                    # Wait for page to load after redirect
                    time.sleep(self.config.timing.PAGE_LOAD_WAIT)
                else:
                    # No more redirects happening
                    time.sleep(1)  # Small wait to check once more
                    if self.driver.current_url == last_url:
                        break
            except Exception:
                # No more redirects happening
                break
        
        return True
    
    def _check_authentication(self) -> bool:
        """
        Check if the current page indicates successful authentication.
        
        Returns:
            True if authentication appears successful
        """
        try:
            # Check if we're on the Vogue domain
            if "vogue.com" in self.driver.current_url:
                # Look for typical post-auth elements
                auth_indicators = [
                    "NavigationWrapper",
                    "SummaryItemWrapper",
                    "FashionShowsIndex"
                ]
                
                for indicator in auth_indicators:
                    try:
                        elements = self.driver.find_elements(By.CLASS_NAME, indicator)
                        if elements and len(elements) > 0:
                            self.logger.info(f"Found authentication indicator: {indicator}")
                            return True
                    except:
                        continue
            
            # Check for auth completion URL
            if "auth/complete" in self.driver.current_url:
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking authentication: {str(e)}")
            return False
    
    def verify_authentication(self) -> bool:
        """
        Verify authentication by navigating to a protected page.
        
        Returns:
            True if authentication is confirmed
        """
        try:
            # Navigate to fashion shows page
            test_url = f"{self.config.BASE_URL}/fashion-shows"
            self.driver.get(test_url)
            self.logger.info(f"Verifying authentication at: {test_url}")
            
            # Wait for page load
            time.sleep(self.config.timing.PAGE_LOAD_WAIT)
            
            # Check for paywall indicators
            if self._check_paywall_indicators():
                self.logger.warning("Paywall detected - Authentication failed")
                return False
            
            # Check for authenticated content
            return self._verify_authenticated_content()
            
        except Exception as e:
            self.logger.error(f"Error verifying authentication: {str(e)}")
            return False
    
    def _check_paywall_indicators(self) -> bool:
        """
        Check for presence of paywall indicators.
        
        Returns:
            True if paywall indicators are found
        """
        paywall_indicators = ["subscribe-wall", "paywall", "subscription-prompt"]
        
        for indicator in paywall_indicators:
            try:
                elements = self.driver.find_elements(
                    By.CSS_SELECTOR, 
                    f"[class*='{indicator}'], [id*='{indicator}']"
                )
                
                for element in elements:
                    if element.is_displayed():
                        self.logger.warning(f"Found paywall indicator: {indicator}")
                        return True
            except:
                continue
                
        return False
    
    def _verify_authenticated_content(self) -> bool:
        """
        Verify presence of authenticated content.
        
        Returns:
            True if authenticated content is found
        """
        try:
            # Look for designer items
            try:
                designer_items = WebDriverWait(self.driver, self.config.timing.ELEMENT_WAIT).until(
                    EC.presence_of_all_elements_located((
                        By.CLASS_NAME, self.config.selectors.DESIGNER_ITEM
                    ))
                )
                
                if designer_items and len(designer_items) > 0:
                    self.logger.info(f"Found {len(designer_items)} designer items")
                    return True
            except:
                pass
            
            # Alternative check for navigation elements
            try:
                nav_elements = self.driver.find_elements(
                    By.CLASS_NAME, self.config.selectors.NAVIGATION_WRAPPER
                )
                if nav_elements and len(nav_elements) > 0:
                    self.logger.info("Found navigation elements")
                    return True
            except:
                pass
            
            self.logger.warning("No authenticated content found")
            return False
            
        except Exception as e:
            self.logger.error(f"Error verifying authenticated content: {str(e)}")
            return False