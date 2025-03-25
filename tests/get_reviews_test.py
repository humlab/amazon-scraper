import logging

from amazon_scraper.amazon_scraper import get_reviews


def test_get_reviews_when_no_reviews(driver, caplog):
    asin = "B005MTXL46"
    base_url = "https://www.amazon.com"

    with caplog.at_level(logging.WARNING):
        reviews = get_reviews(driver, base_url, asin, "positive")

    assert reviews is None

    log_messages = [record.message for record in caplog.records]
    assert f"Reviews button not found for ASIN: {asin}" in log_messages
