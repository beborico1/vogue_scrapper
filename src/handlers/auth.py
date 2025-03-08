# src/handlers/auth.py
"""Authentication handling for Vogue Runway scraper."""

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from ..config.settings import AUTH_WAIT, PAGE_LOAD_WAIT, ELEMENT_WAIT, SELECTORS
from ..exceptions.errors import AuthenticationError, ElementNotFoundError
from ..utils.wait_utils import wait_for_page_load, wait_for_url_change


class VogueAuthHandler:
    """Handles authentication for Vogue Runway."""

    def __init__(self, driver, logger, base_url: str):
        """Initialize the auth handler."""
        self.driver = driver
        self.logger = logger
        self.base_url = base_url

    def authenticate(self, auth_url: str) -> bool:
        """Handle the authentication process."""
        self.logger.info("Starting authentication process...")

        try:
            self.driver.get(auth_url)
            # Wait for document to finish loading
            wait_for_page_load(self.driver, timeout=PAGE_LOAD_WAIT)
            
            current_url = self.driver.current_url
            self.logger.info(f"Initial navigation complete. Current URL: {current_url}")

            if not self._handle_redirects():
                return False

            if "vogue.com/auth/complete" in self.driver.current_url:
                self.logger.info("Authentication successful - Found completion URL")
                return True

            if "id.condenast.com" in self.driver.current_url:
                self._handle_login_form()

            if not self.verify_authentication():
                raise AuthenticationError("Failed to verify authentication status")

            return True

        except Exception as e:
            raise AuthenticationError(f"Authentication failed: {str(e)}") from e

    def _handle_redirects(self) -> bool:
        """Handle authentication redirects."""
        max_redirects = 5
        redirect_count = 0
        last_url = self.driver.current_url

        while redirect_count < max_redirects:
            try:
                # Wait for URL to change (indicating a redirect)
                if wait_for_url_change(self.driver, last_url, timeout=AUTH_WAIT):
                    current_url = self.driver.current_url
                    self.logger.info(f"Redirect {redirect_count + 1}: {current_url}")
                    last_url = current_url
                    redirect_count += 1
                    
                    # Wait for page to load after redirect
                    wait_for_page_load(self.driver, timeout=PAGE_LOAD_WAIT)
                else:
                    # No more redirects happening
                    break
            except TimeoutException:
                # No more redirects happening
                break

        return True

    def _handle_login_form(self):
        """Handle Condé Nast login form."""
        try:
            # Wait for the login form to appear
            WebDriverWait(self.driver, timeout=ELEMENT_WAIT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "form[action*='condenast']"))
            )
            raise AuthenticationError("Manual authentication required")
        except TimeoutException:
            self.logger.error("Unable to detect login form")

    def verify_authentication(self) -> bool:
        """Verify authentication status."""
        try:
            test_url = f"{self.base_url}/fashion-shows"
            self.driver.get(test_url)
            
            # Wait for page to load
            wait_for_page_load(self.driver, timeout=PAGE_LOAD_WAIT)

            if self._check_paywall_indicators():
                return False

            return self._verify_authenticated_content()

        except Exception as e:
            self.logger.error(f"Error verifying authentication: {str(e)}")
            return False

    def _check_paywall_indicators(self) -> bool:
        """Check for presence of paywall indicators."""
        paywall_indicators = ["subscribe-wall", "paywall", "subscription-prompt"]
        for indicator in paywall_indicators:
            try:
                # Use a short timeout for checking paywall indicators
                element = WebDriverWait(self.driver, timeout=2).until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR, f"[class*='{indicator}'], [id*='{indicator}']"
                    ))
                )
                if element.is_displayed():
                    self.logger.warning(f"Found paywall indicator: {indicator}")
                    return True
            except (NoSuchElementException, TimeoutException):
                continue
        return False

    def _verify_authenticated_content(self) -> bool:
        """Verify presence of authenticated content."""
        try:
            # Wait for designer items to appear (indicates authenticated content)
            designer_items = WebDriverWait(self.driver, timeout=ELEMENT_WAIT).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, SELECTORS["designer_item"]))
            )
            if designer_items:
                self.logger.info("Found authenticated content")
                return True
        except (NoSuchElementException, TimeoutException):
            self.logger.warning("No authenticated content found")
        return False