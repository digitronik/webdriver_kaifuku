"""Base class for restartable browser managers."""

import logging
from abc import ABC, abstractmethod
from typing import Any

log = logging.getLogger(__name__)


class BaseManager(ABC):
    """
    Base class for restartable browser instances.

    Provides automatic recovery from browser crashes or unresponsive states.
    All browser managers must implement this interface to provide kaifuku
    (recovery) functionality.
    """

    @abstractmethod
    def start(self) -> Any:
        """
        Starts a fresh browser instance.

        If a browser is already open, it should be closed first.

        Returns:
            The browser driver or page object.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Closes the browser instance and cleans up resources.
        """
        pass

    quit = close

    @property
    @abstractmethod
    def is_alive(self) -> bool:
        """
        Checks if the browser is still responsive.

        Returns:
            bool: True if browser is alive and responsive, False otherwise.
        """
        pass

    @abstractmethod
    def ensure_open(self) -> Any:
        """
        Ensures browser is open and responsive, auto-recovering if needed.

        This is the main method for restartable instances. If the browser
        has crashed or become unresponsive, it will automatically recover.

        Returns:
            The browser driver or page object.
        """
        pass

    def recover(self):
        """
        Recovers from a crashed or unresponsive browser instance.

        Safely closes the dead session (ignoring errors) and starts fresh.
        This is the core of the kaifuku (recovery) functionality.

        Returns:
            A new browser driver or page object.
        """
        log.warning(f"Recovering {self.__class__.__name__} instance...")
        try:
            self.close()
        except Exception as e:
            log.warning(f"Ignoring error during close-on-recover: {e}")

        return self.start()
