"""Modul obsahující věci kolem Selenia."""

from __future__ import annotations

from enum import Enum

from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver

__all__ = ["Browser", "SeleniumHandler"]


class Browser(Enum):
    """Enum prohlížečů/browserů podporovaných Seleniem"""

    CHROME = 0
    FIREFOX = 1
    EDGE = 2
    SAFARI = 3
    OPERA = 4
    IE = 5


class SeleniumHandler:
    """Třída obsahujcí nastavení pro Selenium."""

    def __init__(
        self,
        browser: Browser,
        executable_path: str | None = None,
        params: dict | None = None,
    ):
        self.browser: Browser = browser
        self.executable_path: str | None = executable_path
        self.params: dict = {} if params is None else params

    def open(self, try_silent: bool = True) -> WebDriver:
        """Spustí a vrátí WebDriver instanci"""
        # try_silent = False # Pouze pro debugování
        driver: WebDriver
        if self.browser == Browser.CHROME:
            options_chrome = webdriver.ChromeOptions()
            if try_silent:
                options_chrome.set_headless(True)
            driver = webdriver.Chrome(options=options_chrome, **self._builded_params)
        elif self.browser == Browser.FIREFOX:
            options_firefox = webdriver.FirefoxOptions()
            if try_silent:
                options_firefox.set_headless(True)
            driver = webdriver.Firefox(options=options_firefox, **self._builded_params)
        elif self.browser == Browser.EDGE:
            driver = webdriver.Edge(**self._builded_params)
        elif self.browser == Browser.SAFARI:
            driver = webdriver.Safari(**self._builded_params)
        elif self.browser == Browser.OPERA:
            driver = webdriver.Opera(**self._builded_params)
        elif self.browser == Browser.IE:
            options_ie = webdriver.IeOptions()
            driver = webdriver.Ie(options=options_ie, **self._builded_params)
        else:
            raise ValueError()
        return driver

    def build_params(self):
        path = (
            {"executable_path": self.executable_path}
            if self.executable_path is not None
            else {}
        )
        self._builded_params = {**path, **self.params}
