"""
webdriver_kaifuku - Restartable webdriver instances.

Provides automatic recovery for browser instances that crash or become
unresponsive. Supports both Selenium WebDriver and Playwright.

The name 'kaifuku' (回復) means 'recovery' or 'restoration' in Japanese.
"""

from copy import copy

from .base import BaseManager
from .playwright_manager import PlaywrightManager
from .selenium_manager import SeleniumManager


class BrowserManager:
    """
    Creates restartable browser instances with automatic recovery.

    Returns a manager (SeleniumManager or PlaywrightManager) that
    automatically recovers from browser crashes or unresponsive states.

    Usage:
        manager = BrowserManager.from_conf(config)
        driver = manager.ensure_open()  # Auto-recovers if browser dies
        ...
        manager.close()
    """

    @staticmethod
    def from_conf(browser_conf: dict) -> BaseManager:
        """
        Creates a restartable browser manager from configuration.

        Args:
            browser_conf (dict): Configuration with 'driver_type' key
                                ('selenium' or 'playwright'). Defaults to 'selenium'.

        Returns:
            BaseManager: Restartable manager instance with automatic recovery.
        """
        config = copy(browser_conf)
        driver_type = config.get("driver_type", "selenium")

        if driver_type == "playwright":
            return PlaywrightManager.from_conf(config)
        elif driver_type == "selenium":
            return SeleniumManager.from_conf(config)
        else:
            raise ValueError(
                f"Unknown driver_type in config: '{driver_type}'. "
                "Must be 'selenium' or 'playwright'."
            )


__all__ = ["BrowserManager", "BaseManager", "SeleniumManager", "PlaywrightManager"]
