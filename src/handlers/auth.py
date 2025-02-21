# handlers/auth.py
"""Authentication handling for Vogue Runway scraper."""

import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from ..config.settings import AUTH_WAIT, PAGE_LOAD_WAIT, ELEMENT_WAIT, SELECTORS
from ..exceptions.errors import AuthenticationError, ElementNotFoundError


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
            time.sleep(AUTH_WAIT)
            current_url = self.driver.current_url

            if current_url == last_url:
                break

            self.logger.info(f"Redirect {redirect_count + 1}: {current_url}")
            last_url = current_url
            redirect_count += 1

        return True

    def _handle_login_form(self):
        """Handle Condé Nast login form."""
        try:
            login_form = self.driver.find_element(By.CSS_SELECTOR, "form[action*='condenast']")
            if login_form:
                raise AuthenticationError("Manual authentication required")
        except NoSuchElementException:
            self.logger.error("Unable to detect login form")

    def verify_authentication(self) -> bool:
        """Verify authentication status."""
        try:
            test_url = f"{self.base_url}/fashion-shows"
            self.driver.get(test_url)
            time.sleep(PAGE_LOAD_WAIT)

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
                element = self.driver.find_element(
                    By.CSS_SELECTOR, f"[class*='{indicator}'], [id*='{indicator}']"
                )
                if element.is_displayed():
                    self.logger.warning(f"Found paywall indicator: {indicator}")
                    return True
            except NoSuchElementException:
                continue
        return False

    def _verify_authenticated_content(self) -> bool:
        """Verify presence of authenticated content."""
        try:
            designer_items = self.driver.find_elements(By.CLASS_NAME, SELECTORS["designer_item"])
            if designer_items:
                self.logger.info("Found authenticated content")
                return True
        except NoSuchElementException:
            self.logger.warning("No authenticated content found")
        return False
