import os
from unittest import mock

import pytest

from amazon_scraper.scrape_utility import find_element, get_driver


def test_find_element(driver):
    driver.get("https://www.amazon.com")
    element = find_element(driver, "search_box")
    assert element is not None
    driver.quit()


@pytest.mark.slow
def test_get_driver_headless():
    driver = get_driver()
    assert driver is not None
    assert driver.capabilities['moz:headless'] is True
    driver.quit()


@mock.patch.dict(os.environ, {"FIREFOX_EXECUTABLE_PATH": ""})
def test_get_driver_without_env_var():
    with pytest.raises(ValueError, match="FIREFOX_EXECUTABLE_PATH not set in .env file"):
        get_driver()
