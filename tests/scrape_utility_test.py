from amazon_scraper.scrape_utility import find_element


def test_find_element(driver):
    driver.get("https://www.amazon.com")
    element = find_element(driver, "search_box")
    assert element is not None
    driver.quit()
