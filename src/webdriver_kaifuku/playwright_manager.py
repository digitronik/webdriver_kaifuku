"""Restartable Playwright browser instances."""

from __future__ import annotations

import logging
from typing import Callable

from attrs import define, field
from playwright.sync_api import Browser, BrowserContext, Error, Page, Playwright, sync_playwright

from .base import BaseManager

log = logging.getLogger(__name__)


@define(auto_attribs=True)
class PlaywrightManager(BaseManager):
    """
    Restartable Playwright browser instances with automatic recovery.

    Provides kaifuku (recovery) functionality for Playwright, automatically
    recovering from browser crashes or unresponsive states.
    """

    config: dict = field()
    page: Page | None = field(default=None, init=False)

    # Internal Playwright objects
    _playwright: Playwright | None = field(default=None, init=False)
    _browser: Browser | None = field(default=None, init=False)
    _context: BrowserContext | None = field(default=None, init=False)

    # Cleanup callbacks stored in manager (Page objects don't support arbitrary attributes)
    _cleanup_callbacks: list[Callable] = field(factory=list, init=False)

    @classmethod
    def from_conf(cls, browser_conf: dict) -> PlaywrightManager:
        """
        Creates a PlaywrightManager from configuration dictionary.

        Args:
            browser_conf: Configuration dictionary containing Playwright settings

        Returns:
            PlaywrightManager instance
        """
        from copy import copy

        config = copy(browser_conf)
        log.debug(config)
        return cls(config)

    def start(self) -> Page:
        """
        Starts a fresh Playwright browser instance.

        If a page is already open, it closes it first before creating a new one.

        Returns:
            A new Playwright Page object.
        """
        if self.page is not None:
            self.quit()
        return self.open_fresh()

    def open_fresh(self) -> Page:
        """
        Opens a fresh Playwright browser instance.

        Assumes no page is currently open.

        Returns:
            A new Playwright Page object.
        """
        log.info("Starting Playwright...")
        assert self.page is None

        try:
            self._playwright = sync_playwright().start()

            ws_endpoint = self.config.get("ws_endpoint")
            browser_name = self.config.get("browser", "chromium")

            if ws_endpoint:
                # --- REMOTE LOGIC ---
                log.info(f"Connecting to remote Playwright at: {ws_endpoint}")
                connect_options = self.config.get("connect_options", {})

                if browser_name in ["chromium", "chrome"]:
                    self._browser = self._playwright.chromium.connect(
                        ws_endpoint, **connect_options
                    )
                elif browser_name == "firefox":
                    self._browser = self._playwright.firefox.connect(ws_endpoint, **connect_options)
                elif browser_name == "webkit":
                    self._browser = self._playwright.webkit.connect(ws_endpoint, **connect_options)
                else:
                    raise ValueError(f"Unknown Playwright browser: {browser_name}")

            else:
                # --- LOCAL LOGIC ---
                log.info(f"Launching local Playwright {browser_name} browser...")
                launch_options = self.config.get("launch_options", {})

                if browser_name in ["chromium", "chrome"]:
                    self._browser = self._playwright.chromium.launch(**launch_options)
                elif browser_name == "firefox":
                    self._browser = self._playwright.firefox.launch(**launch_options)
                elif browser_name == "webkit":
                    self._browser = self._playwright.webkit.launch(**launch_options)
                else:
                    raise ValueError(f"Unknown Playwright browser: {browser_name}")

            # Context and Page creation is the same for both
            context_options = self.config.get("context_options", {})
            self._context = self._browser.new_context(**context_options)

            # The 'page' is the controllable object
            self.page = self._context.new_page()
            log.info("Playwright Page instance created.")
            return self.page

        except Exception as e:
            log.error(f"Error starting Playwright: {e}")
            self.close()  # Clean up on failure
            raise

    def add_cleanup(self, callback: Callable) -> None:
        """
        Adds a cleanup callback to be executed when the browser closes.
        """
        assert self.page is not None
        self._cleanup_callbacks.append(callback)

    def _consume_cleanups(self) -> None:
        """
        Executes and clears all registered cleanup callbacks.
        """
        while self._cleanup_callbacks:
            self._cleanup_callbacks.pop()()

    def close(self) -> None:
        """
        Closes all Playwright resources.
        """
        self._consume_cleanups()
        log.info("Closing Playwright resources...")
        try:
            if self.page:
                self.page.close()
        except Error:
            pass  # Ignore errors if already closed

        try:
            if self._context:
                self._context.close()
        except Error:
            pass

        try:
            if self._browser:
                self._browser.close()
        except Error:
            pass

        try:
            if self._playwright:
                self._playwright.stop()
        except Error:
            pass

        self.page = None
        self._context = None
        self._browser = None
        self._playwright = None
        self._cleanup_callbacks.clear()

    quit = close

    @property
    def is_alive(self) -> bool:
        """
        Checks if the Playwright page is still responsive.
        """
        log.debug("alive check")
        if self.page is None:
            return False
        return not self.page.is_closed()

    def ensure_open(self) -> Page:
        """
        Ensures the Playwright page is open and responsive.

        Auto-recovers if the page has crashed or become unresponsive.
        """
        if self.is_alive:
            assert self.page is not None
            return self.page
        else:
            return self.recover()
