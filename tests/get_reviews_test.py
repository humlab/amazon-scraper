import pytest
from selenium import webdriver

from amazon_scraper.amazon_scraper import get_reviews


@pytest.fixture
def driver():
    driver = webdriver.Firefox()
    yield driver
    driver.quit()


def test_get_reviews_when_no_reviews(driver):
    asin = "B005MTXL46"
    base_url = "https://www.amazon.com"

    reviews = get_reviews(driver, base_url, asin, "positive")

    assert reviews
