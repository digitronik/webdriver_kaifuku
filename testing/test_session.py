from __future__ import annotations

import subprocess

import requests

from webdriver_kaifuku import PlaywrightManager, SeleniumManager
from webdriver_kaifuku.base import BaseManager


def test_selenium_open_close(test_data: tuple[BaseManager, str]):
    """Test Selenium browser open/close/restart."""
    manager, _ = test_data
    driver = manager.ensure_open()
    driver2 = manager.ensure_open()
    assert driver is driver2
    driver3 = manager.start()
    assert driver3 is not driver2


def test_playwright_open_close(playwright_test_data: tuple[BaseManager, str]):
    """Test Playwright browser open/close/restart."""
    manager, _ = playwright_test_data
    page = manager.ensure_open()
    page2 = manager.ensure_open()
    assert page is page2
    page3 = manager.start()
    assert page3 is not page2


def test_selenium_session(test_data: tuple[BaseManager, str], selenium_container: str):
    """Test Selenium-specific session capabilities."""
    manager, browser_name = test_data
    assert isinstance(manager, SeleniumManager)

    driver = manager.ensure_open()
    r = requests.get("http://localhost:4444/status")
    assert r.ok
    assert driver.caps["acceptInsecureCerts"] is True
    assert driver.caps["browserName"] == browser_name
    if browser_name == "firefox":
        assert driver.caps["proxy"] == {
            "httpProxy": "example.com:8080",
            "proxyType": "MANUAL",
            "sslProxy": "example.com:8080",
        }
        assert manager.browser_factory.webdriver_kwargs["options"].preferences == {
            "remote.active-protocols": 1,
            "privacy.trackingprotection.enabled": False,
            "browser.contentblocking.enabled": False,
            "browser.privatebrowsing.autostart": True,
        }
        assert manager.browser_factory.webdriver_kwargs["options"].arguments == ["-private"]
    if browser_name == "chrome":
        assert driver.caps["goog:loggingPrefs"] == {"browser": "INFO", "performance": "ALL"}
        ps = subprocess.run(
            [
                "podman",
                "exec",
                selenium_container,
                "bash",
                "-c",
                "for ps in $(ls /proc | grep -e [0-9]); do cat /proc/$ps/cmdline; echo; done",
            ],
            capture_output=True,
        )
        commands = ps.stdout.decode("utf-8").splitlines()
        chrome = [
            c
            for c in commands
            if "/opt/google/chrome/chrome" in c
            and "--no-sandbox" in c
            and "--proxy-server=example.com:8080" in c
        ]
        assert chrome


def test_playwright_session(playwright_test_data: tuple[BaseManager, str]):
    """Test Playwright remote session capabilities."""
    manager, browser_name = playwright_test_data
    assert isinstance(manager, PlaywrightManager)

    page = manager.ensure_open()
    assert not page.is_closed()

    context = page.context
    browser = context.browser
    assert browser is not None

    expected_browser = "chromium" if browser_name == "chrome" else browser_name
    assert browser.browser_type.name == expected_browser

    page.goto("https://example.com")
    assert "example.com" in page.url
    assert "Example Domain" in page.title()

    if browser_name == "chromium":
        assert manager.config["context_options"]["ignore_https_errors"] is True


def test_playwright_local_open_close(playwright_local_test_data: tuple[BaseManager, str]):
    """Test local Playwright browser open/close/restart."""
    manager, _ = playwright_local_test_data
    page = manager.ensure_open()
    page2 = manager.ensure_open()
    assert page is page2
    page3 = manager.start()
    assert page3 is not page2


def test_playwright_local_session(playwright_local_test_data: tuple[BaseManager, str]):
    """Test local Playwright session capabilities."""
    manager, browser_name = playwright_local_test_data
    assert isinstance(manager, PlaywrightManager)

    page = manager.ensure_open()
    assert not page.is_closed()

    page.goto("https://example.com")
    assert "example.com" in page.url
    assert "Example Domain" in page.title()


def test_playwright_recovery(playwright_test_data: tuple[BaseManager, str]):
    """Test Playwright recovery mechanism."""
    manager, browser_name = playwright_test_data
    assert isinstance(manager, PlaywrightManager)

    page = manager.ensure_open()
    page.goto("https://example.com")
    assert "example.com" in page.url

    page.close()
    assert page.is_closed()

    page2 = manager.ensure_open()
    assert page2 is not page
    assert not page2.is_closed()

    page2.goto("https://example.com")
    assert "example.com" in page2.url
