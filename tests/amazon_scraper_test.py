import logging

import pytest
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

from amazon_scraper.amazon_scraper import get_image_urls, get_product_info, get_products, get_search_result_pages


@pytest.fixture
def driver():
    options = webdriver.FirefoxOptions()
    options.add_argument('-headless')
    driver = webdriver.Firefox(options=options)
    yield driver
    driver.quit()


@pytest.mark.web
class TestGetSearchResultPages:
    @pytest.mark.slow
    def test_get_search_result_pages_with_only_one_result_page(self, driver, caplog):
        base_url = "https://www.amazon.com"
        keyword = "nonexistentproduct12345"
        max_search_result_pages = 1

        with caplog.at_level(logging.INFO):
            search_result_pages = get_search_result_pages(driver, base_url, keyword, max_search_result_pages)

        assert len(search_result_pages) == 1
        assert search_result_pages[0].startswith(f"{base_url}/s?k={keyword}")
        log_messages = [record.message for record in caplog.records]
        assert "Found only one page." in log_messages

    @pytest.mark.slow
    def test_get_search_result_pages_with_multiple_pages(self, driver, caplog):
        base_url = "https://www.amazon.com"
        keyword = "laptop"
        max_search_result_pages = 3

        with caplog.at_level(logging.INFO):
            search_result_pages = get_search_result_pages(driver, base_url, keyword, max_search_result_pages)

        assert len(search_result_pages) == max_search_result_pages
        assert all(page.startswith(f"{base_url}/s?k={keyword}") for page in search_result_pages)
        log_messages = [record.message for record in caplog.records]
        assert (
            f"Max search result pages set to {max_search_result_pages}. Returning {max_search_result_pages} pages"
            in log_messages
        )

    @pytest.mark.slow
    def test_get_search_result_pages_no_search_box(self, driver, mocker):
        base_url = "https://www.amazon.com"
        keyword = "laptop"
        max_search_result_pages = 1

        mocker.patch('amazon_scraper.scrape_utility.find_element', return_value=None)

        with pytest.raises(NoSuchElementException, match="Search box not found"):
            get_search_result_pages(driver, base_url, keyword, max_search_result_pages)

    @pytest.mark.slow
    def test_get_search_result_pages_with_exception(self, driver, mocker, caplog):
        base_url = "https://www.amazon.com"
        keyword = "laptop"
        max_search_result_pages = 1

        mocker.patch('amazon_scraper.scrape_utility.find_attribute', side_effect=Exception)

        with caplog.at_level(logging.INFO):
            search_result_pages = get_search_result_pages(driver, base_url, keyword, max_search_result_pages)

        assert len(search_result_pages) == 1
        assert search_result_pages[0].startswith(f"{base_url}/s?k={keyword}")
        assert caplog.records[0].message.startswith("Error getting search result pages: ")


@pytest.mark.web
class TestGetProducts:
    @pytest.mark.slow
    def test_get_products_with_valid_page(self, driver, tmp_path):
        base_url = "https://www.amazon.com"
        page_url = "https://www.amazon.com/s?k=laptop"
        filename = "test_page.png"
        screenshot_path = tmp_path / filename

        products = get_products(driver, page_url, base_url, filename=str(screenshot_path))

        assert len(products) > 0
        assert all("title" in product for product in products)
        assert all("price" in product for product in products)
        assert all("url" in product for product in products)
        assert all("asin" in product for product in products)
        assert all("simplified_url" in product for product in products)
        assert all("is_sponsored" in product for product in products)

        assert screenshot_path.exists()
        assert screenshot_path.is_file()
        assert screenshot_path.stat().st_size > 0

    @pytest.mark.slow
    def test_get_products_with_no_products(self, driver, mocker, tmp_path):
        base_url = "https://www.amazon.com"
        page_url = "https://www.amazon.com/s?k=nonexistentproduct1234567890"
        filename = "test_page.png"
        screenshot_path = tmp_path / filename

        mocker.patch('selenium.webdriver.remote.webdriver.WebDriver.find_elements', return_value=[])

        products = get_products(driver, page_url, base_url, filename=str(screenshot_path))

        assert len(products) == 0
        assert screenshot_path.exists()
        assert screenshot_path.is_file()
        assert screenshot_path.stat().st_size > 0

    @pytest.mark.slow
    def test_get_products_with_no_such_element_exception(self, driver, mocker, caplog, tmp_path):
        base_url = "https://www.amazon.com"
        page_url = "https://www.amazon.com/s?k=laptop"
        filename = "test_page.png"
        screenshot_path = tmp_path / filename

        mocker.patch('amazon_scraper.scrape_utility.find_attribute', side_effect=NoSuchElementException)

        with caplog.at_level(logging.INFO):
            products = get_products(driver, page_url, base_url, filename=str(screenshot_path))

        assert len(products) == 0
        assert screenshot_path.exists()
        assert screenshot_path.is_file()
        assert screenshot_path.stat().st_size > 0
        assert caplog.records[0].message.startswith("Error processing product: ")
        assert caplog.records[-1].message.startswith("Processed 0 products on page")


@pytest.mark.web
class TestGetProductInfo:
    @pytest.mark.slow
    def test_get_product_info_with_valid_url(self, driver):
        product_url = "https://www.amazon.com/dp/B0B9YVG4LR"
        product_info = get_product_info(driver, product_url)

        assert len(product_info) == 13


@pytest.mark.web
class TestGetImageUrls:
    @pytest.mark.slow
    def test_get_image_urls(self, driver):
        image_urls = get_image_urls(driver, "https://www.amazon.com/dp/B0B9YVG4LR")

        assert len(image_urls) == 7
        assert all(
            image_url.startswith("https://m.media-amazon.com/images/I/")
            for image_url in image_urls
            if isinstance(image_url, str)
        )
        assert all(image_url.endswith(".jpg") for image_url in image_urls if isinstance(image_url, str))
