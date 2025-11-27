import contextlib
import logging
import subprocess
from importlib.metadata import version
from urllib.request import urlopen

import pytest
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from wait_for import wait_for

log = logging.getLogger(__name__)

SELENIUM_IMAGE = "quay.io/redhatqe/selenium-standalone:latest"
# Trying to match server playwright version with client.
PLAYWRIGHT_IMAGE = f"docker.io/digitronik/playwright-vnc:{version('playwright')}"
SELENIUM_PORT = 4444
PLAYWRIGHT_PORT = 3000

_CHROME_OPTIONS = ChromeOptions()
_CHROME_OPTIONS.set_capability("acceptInsecureCerts", True)
_CHROME_OPTIONS.add_argument("--disable-application-cache")

_FIREFOX_OPTIONS = FirefoxOptions()
_FIREFOX_OPTIONS.set_capability("acceptInsecureCerts", True)
_FIREFOX_OPTIONS.set_preference("privacy.trackingprotection.enabled", False)
_FIREFOX_OPTIONS.set_preference("browser.contentblocking.enabled", False)
_FIREFOX_OPTIONS.set_preference("browser.privatebrowsing.autostart", True)
_FIREFOX_OPTIONS.add_argument("-private")


SELENIUM_CONFIGS = [
    pytest.param(
        (
            {
                "webdriver": "Remote",
                "proxy_url": "http://example.com:8080",
                "webdriver_options": {
                    "command_executor": f"http://127.0.0.1:{SELENIUM_PORT}",
                    "desired_capabilities": {
                        "browserName": "firefox",
                        "acceptInsecureCerts": True,
                        "firefoxOptions": {
                            "prefs": {
                                "privacy.trackingprotection.enabled": False,
                                "browser.contentblocking.enabled": False,
                                "browser.privatebrowsing.autostart": True,
                            },
                            "args": ["-private"],
                        },
                    },
                },
            },
            "firefox",
        ),
        id="remote-firefox",
    ),
    pytest.param(
        (
            {
                "webdriver": "Remote",
                "proxy_url": "http://example.com:8080",
                "webdriver_options": {
                    "command_executor": f"http://127.0.0.1:{SELENIUM_PORT}",
                    "desired_capabilities": {
                        "browserName": "chrome",
                        "acceptInsecureCerts": True,
                        "chromeOptions": {
                            "args": ["--disable-application-cache"],
                        },
                        "goog:loggingPrefs": {"browser": "INFO", "performance": "ALL"},
                    },
                },
            },
            "chrome",
        ),
        id="remote-chrome",
    ),
    pytest.param(
        (
            {
                "webdriver": "Remote",
                "proxy_url": "http://example.com:8080",
                "webdriver_options": {
                    "command_executor": f"http://127.0.0.1:{SELENIUM_PORT}",
                    "options": _FIREFOX_OPTIONS,
                },
            },
            "firefox",
        ),
        id="remote-firefox-options",
    ),
    pytest.param(
        (
            {
                "webdriver": "Remote",
                "proxy_url": "http://example.com:8080",
                "webdriver_options": {
                    "command_executor": f"http://127.0.0.1:{SELENIUM_PORT}",
                    "options": _CHROME_OPTIONS,
                    "desired_capabilities": {
                        "browserName": "chrome",
                        "goog:loggingPrefs": {"browser": "INFO", "performance": "ALL"},
                    },
                },
            },
            "chrome",
        ),
        id="remote-chrome-options",
    ),
]


@pytest.fixture(scope="session")
def selenium_container():
    ps = subprocess.run(
        [
            "podman",
            "run",
            "--rm",
            "-d",
            "-p",
            f"127.0.0.1:{SELENIUM_PORT}:{SELENIUM_PORT}",
            "--shm-size=2g",
            SELENIUM_IMAGE,
        ],
        capture_output=True,
        text=True,
    )
    if ps.returncode != 0:
        raise RuntimeError(f"Failed to start container: {ps.stderr}")
    container_id = ps.stdout.strip()
    if not container_id:
        raise RuntimeError(f"Container ID is empty. stdout: '{ps.stdout}', stderr: '{ps.stderr}'")
    wait_for(
        lambda: urlopen(f"http://127.0.0.1:{SELENIUM_PORT}"), timeout=180, handle_exception=True
    )
    yield container_id
    if container_id:
        subprocess.run(["podman", "kill", container_id], stdout=subprocess.DEVNULL)


@pytest.fixture(params=SELENIUM_CONFIGS)
def test_data(selenium_container, request: pytest.FixtureRequest):
    from webdriver_kaifuku import BrowserManager

    config, browser_name = request.param  # type: ignore

    mgr = BrowserManager.from_conf(config)  # type: ignore
    log.warning(mgr)
    with contextlib.closing(mgr) as mgr:
        yield mgr, browser_name


PLAYWRIGHT_REMOTE_CONFIGS = [
    pytest.param(
        (
            {
                "driver_type": "playwright",
                "browser": "chromium",
                "ws_endpoint": f"ws://127.0.0.1:{PLAYWRIGHT_PORT}/playwright",
                "context_options": {
                    "ignore_https_errors": True,
                },
            },
            "chromium",
        ),
        id="playwright-remote-chromium",
    ),
    pytest.param(
        (
            {
                "driver_type": "playwright",
                "browser": "firefox",
                "ws_endpoint": f"ws://127.0.0.1:{PLAYWRIGHT_PORT}/playwright",
                "context_options": {
                    "ignore_https_errors": True,
                },
            },
            "firefox",
        ),
        id="playwright-remote-firefox",
    ),
]

PLAYWRIGHT_LOCAL_CONFIGS = [
    pytest.param(
        (
            {
                "driver_type": "playwright",
                "browser": "chromium",
                "launch_options": {
                    "headless": True,
                },
                "context_options": {
                    "ignore_https_errors": True,
                },
            },
            "chromium",
        ),
        id="playwright-local-chromium",
    ),
    pytest.param(
        (
            {
                "driver_type": "playwright",
                "browser": "firefox",
                "launch_options": {
                    "headless": True,
                },
                "context_options": {
                    "ignore_https_errors": True,
                },
            },
            "firefox",
        ),
        id="playwright-local-firefox",
    ),
]


@pytest.fixture(scope="function", params=PLAYWRIGHT_REMOTE_CONFIGS)
def playwright_container(request: pytest.FixtureRequest):
    _, browser_name = request.param  # type: ignore

    ps = subprocess.run(
        [
            "podman",
            "run",
            "--rm",
            "-d",
            "-p",
            f"127.0.0.1:{PLAYWRIGHT_PORT}:{PLAYWRIGHT_PORT}",
            "-e",
            "PW_HEADLESS=true",
            "-e",
            f"PW_BROWSER={browser_name}",
            PLAYWRIGHT_IMAGE,
        ],
        capture_output=True,
        text=True,
    )
    if ps.returncode != 0:
        raise RuntimeError(f"Failed to start Playwright container: {ps.stderr}")
    container_id = ps.stdout.strip()
    if not container_id:
        raise RuntimeError(f"Container ID is empty. stdout: '{ps.stdout}', stderr: '{ps.stderr}'")
    wait_for(
        lambda: urlopen(f"http://127.0.0.1:{PLAYWRIGHT_PORT}/"), timeout=180, handle_exception=True
    )
    yield container_id, request.param
    if container_id:
        subprocess.run(["podman", "kill", container_id], stdout=subprocess.DEVNULL)


@pytest.fixture
def playwright_test_data(playwright_container):
    from webdriver_kaifuku import BrowserManager

    container_id, (config, browser_name) = playwright_container  # type: ignore

    mgr = BrowserManager.from_conf(config)  # type: ignore
    log.warning(mgr)
    with contextlib.closing(mgr) as mgr:
        yield mgr, browser_name


@pytest.fixture(params=PLAYWRIGHT_LOCAL_CONFIGS)
def playwright_local_test_data(request: pytest.FixtureRequest):
    from webdriver_kaifuku import BrowserManager

    config, browser_name = request.param  # type: ignore

    mgr = BrowserManager.from_conf(config)  # type: ignore
    log.warning(mgr)
    with contextlib.closing(mgr) as mgr:
        yield mgr, browser_name
