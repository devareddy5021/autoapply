import os
import logging
from typing import Optional
from pathlib import Path
from django.conf import settings
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright

logger = logging.getLogger(__name__)


class BrowserManager:
    """
    Manages Playwright lifecycle and browser context.
    Supports persistent browser profile storage so external website logins
    remain active without credentials ever touching Django.
    """
    def __init__(self, headless: Optional[bool] = None, user_data_dir: Optional[str] = None):
        if headless is None:
            self.headless = getattr(settings, 'PLAYWRIGHT_HEADLESS', False)
        else:
            self.headless = headless

        self.user_data_dir = user_data_dir or getattr(settings, 'BROWSER_PROFILE_DIR', None)
        if self.user_data_dir:
            Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    def start(self) -> Page:
        """Starts Playwright and returns an active, configured Page instance."""
        self._playwright = sync_playwright().start()

        launch_args = [
            '--disable-blink-features=AutomationControlled',
            '--start-maximized',
        ]

        if self.user_data_dir:
            try:
                # Persistent context saves cookies/sessions to disk
                self._context = self._playwright.chromium.launch_persistent_context(
                    user_data_dir=str(self.user_data_dir),
                    headless=self.headless,
                    args=launch_args,
                    viewport={'width': 1280, 'height': 850},
                    user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                pages = self._context.pages
                self._page = pages[0] if pages else self._context.new_page()
                logger.info(f"Browser launched with persistent context at {self.user_data_dir} (headless={self.headless})")
                return self._page
            except Exception as e:
                logger.warning(f"Persistent context launch failed ({e}); falling back to ephemeral browser context")

        # Standard browser launch fallback
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            args=launch_args
        )
        self._context = self._browser.new_context(
            viewport={'width': 1280, 'height': 850},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        self._page = self._context.new_page()
        logger.info(f"Browser launched with ephemeral context (headless={self.headless})")
        return self._page

    @property
    def page(self) -> Optional[Page]:
        return self._page

    @property
    def context(self) -> Optional[BrowserContext]:
        return self._context

    def close(self):
        """Clean up and close all browser resources."""
        try:
            if self._page and not self._page.is_closed():
                self._page.close()
        except Exception:
            pass

        try:
            if self._context:
                self._context.close()
        except Exception:
            pass

        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass

        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass

        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None
        logger.info("Browser session cleanly closed.")

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
