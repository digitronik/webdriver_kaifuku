from __future__ import annotations

import pytest

from webdriver_kaifuku import BrowserManager, PlaywrightManager, SeleniumManager

SELENIUM_CONFIGS = [
    pytest.param(
        {
            "webdriver": "firefox",
            "webdriver_options": {
                "desired_capabilities": {
                    "browserName": "firefox",
                    "acceptInsecureCerts": True,
                    "firefoxOptions": {
                        "prefs": {
                            "bar": False,
                        },
                        "args": ["foo"],
                    },
                },
            },
        },
        "firefox",
        id="firefox",
    ),
    pytest.param(
        {
            "webdriver": "chrome",
            "webdriver_options": {
                "desired_capabilities": {
                    "browserName": "chrome",
                    "acceptInsecureCerts": True,
                    "chromeOptions": {
                        "args": ["foo"],
                    },
                },
            },
        },
        "chrome",
        id="chrome",
    ),
]

PLAYWRIGHT_CONFIGS = [
    pytest.param(
        {
            "driver_type": "playwright",
            "browser": "chromium",
            "launch_options": {"headless": True, "args": ["--disable-dev-shm-usage"]},
            "context_options": {
                "ignore_https_errors": True,
                "viewport": {"width": 1920, "height": 1080},
            },
        },
        "chromium",
        id="chromium",
    ),
    pytest.param(
        {
            "driver_type": "playwright",
            "browser": "firefox",
            "launch_options": {"headless": True},
            "context_options": {
                "ignore_https_errors": True,
                "viewport": {"width": 1920, "height": 1080},
            },
        },
        "firefox",
        id="firefox",
    ),
]


@pytest.mark.parametrize("conf,browser_name", SELENIUM_CONFIGS)
def test_selenium_initializing_from_config(conf: dict, browser_name: str):
    manager = BrowserManager.from_conf(conf)
    assert isinstance(manager, SeleniumManager)

    args = manager.browser_factory.processed_browser_args()
    options = args["options"]

    assert options.capabilities.get("acceptInsecureCerts") is True
    assert options.arguments == ["foo"]
    if browser_name == "firefox":
        assert options.preferences == {"remote.active-protocols": 1, "bar": False}


@pytest.mark.parametrize("conf,browser_name", PLAYWRIGHT_CONFIGS)
def test_playwright_initializing_from_config(conf: dict, browser_name: str):
    manager = BrowserManager.from_conf(conf)
    assert isinstance(manager, PlaywrightManager)

    assert manager.config["browser"] == browser_name
    assert "context_options" in manager.config
    assert manager.config["context_options"]["ignore_https_errors"] is True

    assert "viewport" in manager.config["context_options"]
    assert manager.config["context_options"]["viewport"]["width"] == 1920
    assert manager.config["context_options"]["viewport"]["height"] == 1080
