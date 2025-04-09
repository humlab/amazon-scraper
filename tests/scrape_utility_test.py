import os
from unittest import mock

import pytest

from amazon_scraper.scrape_utility import find_element, get_driver


class TestGetDriver:
    @pytest.mark.slow
    def test_get_driver_headless(self):
        driver = get_driver()
        assert driver is not None
        assert driver.capabilities['moz:headless'] is True
        driver.quit()

    @pytest.mark.skip(reason="This test requires a valid path to the geckodriver executable.")
    def test_get_driver_with_env_var(self):
        with mock.patch.dict(os.environ, {"FIREFOX_EXECUTABLE_PATH": "/snap/bin/firefox.geckodriver"}):
            driver = get_driver()
            assert driver is not None
            assert driver.capabilities['moz:headless'] is True
            driver.quit()

    def test_get_driver_with_invalid_env_var(self):
        with mock.patch.dict(os.environ, {"FIREFOX_EXECUTABLE_PATH": "/invalid/path/to/firefox"}):
            with pytest.raises(ValueError, match="The path is not a valid file"):
                get_driver()

    @mock.patch.dict(os.environ, {"FIREFOX_EXECUTABLE_PATH": ""})
    def test_get_driver_without_env_var(self):
        with pytest.raises(ValueError, match="FIREFOX_EXECUTABLE_PATH not set in .env file"):
            get_driver()

    def test_get_driver_with_webdriver_manager(self):
        driver = get_driver(use_webdriver_manager=True)
        assert driver is not None
        assert driver.capabilities['moz:headless'] is True
        driver.quit()


def test_find_element(driver):
    driver.get("https://www.amazon.com")
    element = find_element(driver, "search_box")
    assert element is not None
    driver.quit()
