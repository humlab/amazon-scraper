import pytest
from selenium import webdriver

from amazon_scraper.scrape_utility import find_element


@pytest.fixture(name="driver")
def fixture_driver():
    options = webdriver.FirefoxOptions()
    options.add_argument('-headless')
    driver = webdriver.Firefox(options=options)
    yield driver
    driver.quit()


def test_find_element(driver):
    driver.get("https://www.amazon.com")
    element = find_element(driver, "search_box")
    assert element is not None
    driver.quit()
