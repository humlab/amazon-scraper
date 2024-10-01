# import pytest
# from selenium import webdriver
# from selenium.webdriver.remote.webdriver import WebDriver

# from amazon_scraper.amazon_scraper import get_reviews, load_yaml

# CONFIG = load_yaml("config/selectors.yaml")


# @pytest.fixture
# def driver():
#     driver = webdriver.Firefox()
#     yield driver
#     driver.quit()


# def test_get_reviews(driver):

#     asin = "B0CRHX3CL3"
#     base_url = "https://www.amazon.com"

#     reviews = get_reviews(driver, base_url, asin, "positive")

#     assert reviews
