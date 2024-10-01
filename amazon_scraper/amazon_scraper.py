import csv
import time
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import requests
import yaml
from loguru import logger
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait

from .configuration import ConfigStore, ConfigValue

# CONFIG: dict[str, Any] = {}

ConfigStore.configure_context(source='config/config.yml')


def find_webdriver_parent(
    item: webdriver.remote.webdriver.WebDriver | webdriver.remote.webelement.WebElement, depth: int = 0
) -> webdriver.remote.webdriver.WebDriver | None:
    """Find the parent webdriver object. This function is recursive. The depth parameter is used to prevent infinite recursion.

    Args:
        item (webdriver.remote.webdriver.WebDriver | webdriver.remote.webelement.WebElement): Webdriver object.
        depth (int, optional): Recursion depth. Defaults to 0.

    Returns:
        webdriver.remote.webdriver.WebDriver | None: Parent webdriver object. None if not found.
    """
    if depth > 10:  # FIXME: Handle infinite recursion better
        return None
    if isinstance(item, webdriver.remote.webdriver.WebDriver):
        return item
    if hasattr(item, 'parent'):
        return find_webdriver_parent(item.parent, depth + 1)
    return None


def wait_page_ready(item: webdriver.remote.webdriver.WebDriver | webdriver.remote.webelement.WebElement) -> None:
    """Wait for the page to load.

    Args:
        item (webdriver.remote.webdriver.WebDriver | webdriver.remote.webelement.WebElement): Webdriver object.

    Raises:
        TimeoutError: If the page does not load.

    Returns:
        None
    """
    item = find_webdriver_parent(item)
    if item is None:
        raise ValueError("Parent webdriver object not found")
    try:
        WebDriverWait(item, 30).until(lambda driver: driver.execute_script("return document.readyState") == "complete")
    except TimeoutException as e:
        raise TimeoutError("Page not loaded") from e


def load_yaml(document: str, subset: str | list[str] | None = None) -> Any:
    """Get data from a YAML file. Optionally, get a subset of the data. Subset is a string or a list of keys.

    Args:
        document (str): Document path.
        subset (str or list, optional): String or list of keys. Defaults to None.

    Returns:
        Any: Data from the YAML file.
    """
    with open(document, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        if subset is not None:
            if isinstance(subset, str):
                subset = [subset]
            for key in subset:
                data = data.get(key)
                if data is None:
                    break
            return data
        return data


def find_element(
    item: webdriver.remote.webdriver.WebDriver | webdriver.remote.webelement.WebElement,
    key: str,
    *,
    by: str = By.CSS_SELECTOR,
) -> webdriver.remote.webelement.WebElement | None:
    """Find an element using a key from the selectors.yaml file. The key is used to get a CSS selector or a list of CSS selectors from the selectors.yaml file. The function tries each selector until it finds an element. If no element is found, it returns None.

    Args:
        item (webdriver.remote.webdriver.WebDriver | webdriver.remote.webelement.WebElement): A Selenium WebDriver instance or a WebElement.
        key (str): Key from the selectors.yaml file.
        by (str, optional): Selenium By method. Defaults to By.CSS_SELECTOR.

    Returns:
        webdriver.remote.webelement.WebElement | None: A Selenium WebElement or None.
    """
    selectors: dict[str, Any] = ConfigValue("selectors").resolve()
    config = selectors.get(key)
    if not config:
        return None
    if isinstance(config, str):
        config = [config]

    wait_page_ready(item)

    for selector in config:
        try:
            element = item.find_element(by, selector)
            return element
        except NoSuchElementException:
            logger.debug(f"Element not found: {key}: {selector}. Trying next selector.")
            continue

    logger.debug(f"Element not found: {key}")
    return None


def wait_element(
    item: webdriver.remote.webdriver.WebDriver | webdriver.remote.webelement.WebElement,
    key: str,
    *,
    by: str = By.CSS_SELECTOR,
    timeout: int = 30,
) -> None:
    """Wait for an element to appear on the page. The function tries each selector until it finds an element. If no element is found after the timeout, it raises a NoSuchElementException.

    Args:
        item (webdriver.remote.webdriver.WebDriver | webdriver.remote.webelement.WebElement): A Selenium WebDriver instance or a WebElement.
        key (str): Key from the selectors.yaml file.
        by (str, optional): Selenium By method. Defaults to By.CSS_SELECTOR.
        timeout (int, optional): Timeout in seconds. Defaults to 30.

    Raises:
        NoSuchElementException: If the element is not found after the timeout.
    """
    selectors: dict[str, Any] = ConfigValue("selectors").resolve()

    config = selectors.get(key)
    if not config:
        return
    if isinstance(config, str):
        config = [config]

    for _ in range(0, timeout):
        for selector in config:
            try:
                item.find_element(by, selector)
                return
            except NoSuchElementException:
                continue
        time.sleep(1)  # FIXME: Use WebDriverWait instead

    raise NoSuchElementException(f"Element not found: {key}")


def find_attribute(
    item: webdriver.remote.webdriver.WebDriver | webdriver.remote.webelement.WebElement,
    key: str,
    attribute: str,
    *,
    by: str = By.CSS_SELECTOR,
    default: Any = None,
) -> Any:
    """Find an attribute of an element using a key from the selectors.yaml file. The key is used to get a CSS selector or a list of CSS selectors from the selectors.yaml file. The function tries each selector until it finds an element. If no element is found, it returns the default value.

    Args:
        item (webdriver.remote.webdriver.WebDriver | webdriver.remote.webelement.WebElement): A Selenium WebDriver instance or a WebElement.
        key (str): Key from the selectors.yaml file.
        attribute (str): Attribute name.
        by (str, optional): Selenium By method. Defaults to By.CSS_SELECTOR.
        default (Any, optional): Default value. Defaults to None.

    Returns:
        Any: Attribute value or default value.
    """
    element = find_element(item, key, by=by)
    if element is None:
        return default
    return element.get_attribute(attribute)


def reject_cookies(driver: webdriver.remote.webdriver.WebDriver) -> None:
    """Attempts to find and click a button on a web page to reject cookies using Selenium WebDriver. If the button is found, it clicks the button; otherwise, it does nothing.

    Args:
        driver (webdriver.remote.webdriver.WebDriver): A Selenium WebDriver instance.
    """
    wait_page_ready(driver)
    try:
        cookies_button = find_element(driver, "reject_cookies")
        if cookies_button is not None:
            cookies_button.click()
    except StaleElementReferenceException:
        driver.refresh()
        wait_element(driver, "reject_cookies")
        cookies_button = find_element(driver, "reject_cookies")
        if cookies_button is not None:
            cookies_button.click()


def dismiss_popup(driver: webdriver.remote.webdriver.WebDriver, keyword: str) -> None:
    """Attempts to find and click a button on a web page to dismiss a popup using Selenium WebDriver. If the button is found, it clicks the button; otherwise, it does nothing.

    Args:
        driver (webdriver.remote.webdriver.WebDriver): A Selenium WebDriver instance.
    """
    try:
        popup_button = find_element(driver, keyword)
        if popup_button is not None:
            popup_button.click()
    except StaleElementReferenceException:
        driver.refresh()
        wait_element(driver, keyword)
        popup_button = find_element(driver, keyword)
        if popup_button is not None:
            popup_button.click()


def accept_cookies(driver: webdriver.remote.webdriver.WebDriver) -> None:
    """Attempts to find and click a button on a web page to accept cookies using Selenium WebDriver. If the button is found, it clicks the button; otherwise, it does nothing.

    Args:
        driver (webdriver.remote.webdriver.WebDriver): _description_
    """
    cookies_button = find_element(driver, "accept_cookies")
    if cookies_button is not None:
        cookies_button.click()


def get_search_result_pages(
    driver: webdriver.remote.webdriver.WebDriver, url: str, keyword: str, max_search_result_pages: int | None = None
) -> list[str]:
    """Get search result pages from a search engine.

    Args:
        driver (webdriver.remote.webdriver.WebDriver): A Selenium WebDriver instance.
        url (str): URL of the search engine.
        keyword (str): Search keyword.
        max_search_result_pages (int | None, optional): Maximum number of search result pages. Defaults to None.

    Raises:
        NoSuchElementException: If the search box is not found.
        ValueError: If the number of pages is 0.

    Returns:
        list[str]: List of search result pages.
    """
    driver.get(url)

    wait_element(driver, "search_box")
    search_box = find_element(driver, "search_box")
    if not search_box:
        raise NoSuchElementException("Search box not found")
    search_box.send_keys(keyword)
    search_box.send_keys(Keys.RETURN)

    wait_page_ready(driver)
    reject_cookies(driver)

    wait_element(driver, "number_of_pages")
    attrib = find_attribute(driver, "number_of_pages", "textContent", default='0')

    number_of_pages = int(attrib)
    if number_of_pages == 0:
        raise ValueError("Number of pages is 0")

    number_of_pages = int(find_attribute(driver, "number_of_pages", "textContent", default='1'))

    logger.info(f"Found {number_of_pages} pages")

    number_of_pages = min(number_of_pages, max_search_result_pages) if max_search_result_pages else number_of_pages
    logger.info(f"Max search result pages set to {max_search_result_pages}. Returning {number_of_pages} pages")

    pages = (
        [driver.current_url]
        + [f"{driver.current_url.replace('nb_sb_noss', f'sr_pg_{p}')}&page={p+1}" for p in range(1, number_of_pages)]
        if number_of_pages > 1
        else [driver.current_url]
    )
    return pages


def get_products(driver: webdriver.remote.webdriver.WebDriver, page: str, base_url: str) -> list[dict]:
    """Get products from a search result page.

    Args:
        driver (webdriver.remote.webdriver.WebDriver): A Selenium WebDriver instance.
        page (str): URL of the search result page.
        base_url (str): Base URL of the search engine.

    Returns:
        list[dict]: List of products.
    """
    selectors: dict[str, Any] = ConfigValue("selectors").resolve()

    driver.get(page)
    wait_page_ready(driver)
    elements: list[webdriver.remote.webelement.WebElement] = driver.find_elements(
        By.CSS_SELECTOR, selectors["products"]
    )

    products = []

    for element in elements:

        try:
            product = {
                "title": find_attribute(element, "product_title", "textContent"),
                "price": find_attribute(element, "product_price", "innerText"),  # 'textContent'
                "url": find_attribute(element, "product_url", "href"),
                "asin": (asin := element.get_attribute("data-asin")),
                "simplified_url": f"{base_url}/dp/{asin}",
                "is_sponsored": bool(find_attribute(element, "sponsored", "innerText")),
            }

            products.append(product)
        except NoSuchElementException as e:
            logger.error(f"Error processing product: {e}")
            continue

    logger.info(f"Processed {len(products)} products on page {page}")

    return products


def get_image_urls(driver: webdriver.remote.webdriver.WebDriver, url: str | None = None) -> list[str | None]:
    """Get image links from an Amazon product page.

    Args:
        driver (WebDriver): A Selenium WebDriver instance.
        url (str): URL of the Amazon product page.

    Returns:
        list[str | None]: A list of image links (URLs).
    """
    if url:
        driver.get(url)
        wait_page_ready(driver)

    if driver.current_url == "about:blank":
        raise ValueError("No URL provided")

    if "www.amazon" not in driver.current_url:
        raise ValueError(f"Not an Amazon product page: {driver.current_url}")

    # TODO: Add selector for image links to selectors.yaml. Add find_elements function.
    elements = driver.find_elements(By.CSS_SELECTOR, "#altImages > ul > li")
    elements = [element for element in elements if element.size["height"] != 0]

    actions = ActionChains(driver)

    for element in elements:
        driver.execute_script("arguments[0].scrollIntoView();", element)
        actions.move_to_element(element).perform()  # .click(element)
        time.sleep(1)

    # TODO: Add selector for image links to selectors.yaml. Add find_elements function.
    image_urls = []
    for image in driver.find_element(By.CSS_SELECTOR, "#main-image-container").find_elements(By.TAG_NAME, "img"):
        if image.get_attribute("data-old-hires"):
            image_urls.append(image.get_attribute("data-old-hires"))
        else:
            src = image.get_attribute("src")
            if src and not src.endswith("gif"):
                image_urls.append(src)

    return image_urls


def save_images(urls: list[str], filenames: list[str], directory: str) -> None:
    """Save images from list of image links (URLs) to a directory using a list of filenames.

    Args:
        urls (list[str]): List of image links (URLs).
        filenames (list[str]): List of filenames.
        directory (str): Output directory.
    """
    Path(directory).mkdir(parents=True, exist_ok=True)
    for _, (image_link, filename) in enumerate(zip(urls, filenames)):
        response = requests.get(image_link, timeout=5)
        file_extension = Path(image_link).suffix[1:]
        with open(f"{directory}/{filename}.{file_extension}", "wb") as file:
            file.write(response.content)


def get_product_info(driver: webdriver.remote.webdriver.WebDriver, url: str) -> dict:
    """Get product information from an Amazon product page.

    Args:
        driver (webdriver.remote.webdriver.WebDriver): A Selenium WebDriver instance.
        url (str): URL of the Amazon product page.

    Returns:
        dict: Product information.
    """
    driver.get(url)

    wait_page_ready(driver)

    title = find_attribute(driver, "title", "innerText")
    price = find_attribute(driver, "price", "innerText")
    image_link = find_attribute(driver, "image", "src")
    about = find_attribute(driver, "about", "innerText", default="").strip()

    product_description = find_attribute(driver, "description", "innerText", default="IMAGE_DESCRIPTION_ONLY").strip()

    # FIXME: Check if there are images in the product description
    if find_element(driver, "description"):
        description_image_urls = [
            image.get_attribute("src")
            for image in find_element(driver, "description").find_elements(By.TAG_NAME, "img")
            if not image.get_attribute("src").endswith("gif")
        ]
    else:
        description_image_urls = []

    details = find_attribute(driver, "details", "innerText", default="")
    product_details = {
        key: value
        for line in details.split("\n")
        if (parts := line.split('\t', 1)) and len(parts) == 2
        for key, value in [parts]
    }

    rating = find_attribute(driver, "rating", "innerText", default="").strip()
    number_of_ratings = find_attribute(driver, "number_of_ratings", "innerText", default="")
    number_of_ratings = "".join([c for c in number_of_ratings if c.isdigit()])

    store = find_attribute(driver, "store", "innerText", default="")
    # FIXME: Fix for other domains (e.g. amazon.de, amazon.se). Add to config.
    store = store.replace("Visit the ", "").replace("Brand: ", "").replace(" Store", "").replace(" Brand", "").strip()

    store_url = find_attribute(driver, "store", "href")

    image_urls = get_image_urls(driver)

    return {
        "title_info": title,
        "price_info": price,
        "image_link": image_link,
        "about": about,
        "product_description": product_description,
        "product_details": product_details,
        "rating": rating,
        "number_of_ratings": number_of_ratings,
        "store": store,
        "store_url": store_url,
        "image_urls": image_urls,
        "description_image_urls": description_image_urls or [],
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def get_product_info_by_asin(
    driver: webdriver.remote.webdriver.WebDriver | None = None, *, base_url: str, asin: str
) -> dict:
    """Get product information from an Amazon product page using the ASIN.

    Args:
        base_url (str): Base URL of the search engine.
        asin (str): Amazon Standard Identification Number (ASIN).
        driver (webdriver.remote.webdriver.WebDriver | None, optional): A Selenium WebDriver instance. Defaults to None.

    Returns:
        dict: Product information.
    """
    if driver is None:
        driver = webdriver.Firefox()
    url = f"{base_url}/dp/{asin}"
    return get_product_info(driver, url)


def save_results(results: list[dict], directory: str, base_url: str, keyword: str) -> None:
    """Save results to a CSV file.

    Args:
        results (list[dict]): List of search results.
        directory (str): Output directory.
        base_url (str): Base URL of the search engine.
        keyword (str): Search keyword.
    """
    Path(directory).mkdir(parents=True, exist_ok=True)
    filename = f"{base_url.split('//')[-1].replace('/', '_')}_{keyword}.csv"
    with open(f"{directory}/{filename}", "w", newline='', encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=results[0].keys(), delimiter=";")
        writer.writeheader()
        writer.writerows(results)


def save_webpage_as_png(driver: webdriver.remote.webdriver.WebDriver | None, url: str, filename: str) -> None:
    """Save a webpage as a PNG file.

    Args:
        driver (webdriver.remote.webdriver.WebDriver | None): A Selenium WebDriver instance. Defaults to None.
        url (str): URL of the webpage.
        filename (str): Output filename.
    """
    if driver is None:
        driver = webdriver.Firefox()
    driver.get(url)

    WebDriverWait(driver, 30).until(lambda driver: driver.execute_script("return document.readyState") == "complete")

    reject_cookies(driver)
    dismiss_popup(driver, "dismiss_delivery_options")

    width = driver.execute_script(
        "return Math.max( document.body.scrollWidth, document.body.offsetWidth, document.documentElement.clientWidth, document.documentElement.scrollWidth, document.documentElement.offsetWidth );"
    )

    height = driver.execute_script(
        "return Math.max( document.body.scrollHeight, document.body.offsetHeight, document.documentElement.clientHeight, document.documentElement.scrollHeight, document.documentElement.offsetHeight );"
    )

    driver.set_window_size(width, height)

    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    driver.save_screenshot(filename)


def search_amazon(
    base_url: str,
    keyword: str,
    max_results: int | None = None,
    max_search_result_pages: int | None = None,
    output_directory: str | None = None,
) -> list[dict]:
    """Search Amazon for a keyword and get product information. Optionally, if an output directory is provided, save search result pages as PNG files.

    Args:
        base_url (str): Base URL of the search engine.
        keyword (str): The search keyword.
        max_results (int | None, optional): Maximum number of results. Defaults to None.
        max_search_result_pages (int | None, optional): Maximum number of search result pages. Defaults to None.
        output_directory (str | None, optional): Output directory. If provided, save search result pages as PNG files. Defaults to None.

    Returns:
        list[dict]: List of search results.
    """
    logger.info(f"Searching for {keyword} on {base_url}")

    driver = webdriver.Firefox()

    pages = get_search_result_pages(driver, base_url, keyword, max_search_result_pages)

    if output_directory:
        for index, page in enumerate(pages, start=1):
            save_webpage_as_png(driver, page, f"{output_directory}/search_page_{str(index).zfill(2)}.png")

    search_results = []
    for page in pages:
        search_results += get_products(driver, page, base_url)
        if max_results and len(search_results) >= max_results:
            logger.info(f"Found {max_results} results. Stopping search.")
            break

    if max_results:
        search_results = search_results[:max_results]

    sort_id = 1
    for result in search_results:
        product_info = get_product_info(driver, result["url"])
        result.update(product_info)
        tld = urlparse(base_url).netloc.split('.')[-1]
        result["tld"] = tld
        result["keyword"] = keyword
        result["sort_id"] = f"{str(sort_id).zfill(4)}"
        result["image_names"] = [
            f"{result['sort_id']}{chr(97+index)}.{result['image_urls'][index].split('.')[-1]}"
            for index, _ in enumerate(result["image_urls"])
        ]
        sort_id += 1
    driver.quit()

    return search_results


def save_images_from_results(results: list[dict], directory: str, subdir_key: str) -> None:
    """Save images from a list of search results to a directory. The subdirectory is created using a key from the results.

    Args:
        results (list[dict]): List of search results.
        directory (str): Output directory.
        subdir_key (str): Key to use as subdirectory.
    """
    for result in results:
        subdirectory = result[subdir_key]
        result_directory = f"{directory}/{subdirectory}"
        save_images(result["image_urls"], result["image_names"], result_directory)


def save_description_images(results: list[dict], directory: str, subdir_key: str) -> None:
    """Save description images from a list of search results to a directory. The subdirectory is created using a key from the results.

    Args:
        results (list[dict]): List of search results.
        directory (str): Output directory.
        subdir_key (str): Key to use as subdirectory.
    """
    for result in results:
        subdirectory = result[subdir_key]
        if description_image_urls := result.get("description_image_urls"):
            description_image_names = [
                f"{result['sort_id']}_product_image_{str(i+1).zfill(2)}" for i in range(len(description_image_urls))
            ]
            save_images(description_image_urls, description_image_names, f"{directory}/{subdirectory}")


PossibleSentiments = Literal["1_star", "2_star", "3_star", "4_star", "5_star", "positive", "critical", "all"]


def get_reviews(
    driver: webdriver.remote.webdriver.WebDriver,
    base_url: str,
    asin: str,
    sentiment: PossibleSentiments,
) -> list[dict] | None:
    """Get reviews from an Amazon product page.

    Args:
        driver (webdriver.remote.webdriver.WebDriver): A Selenium WebDriver instance.
        base_url (str): Base URL of the search engine.
        asin (str): Amazon Standard Identification Number (ASIN).
        sentiment (PossibleSentiments): Sentiment of the reviews.

    Raises:
        ValueError: If the reviews button is not found.

    Returns:
        list[dict] | None: List of reviews or None.
    """
    selectors: dict[str, Any] = ConfigValue("selectors").resolve()

    url = f"{base_url}/product-reviews/{asin}"
    driver.get(url)

    wait_page_ready(driver)

    reject_cookies(driver)

    dismiss_popup(driver, "dismiss_delivery_options")

    reviews = []

    # TODO: Add function get_element_with_attribute_value
    reviews_button: webdriver.remote.webelement.WebElement | None = None
    for selector in selectors.get("reviews_stars_button", []):
        if driver.find_element(By.CSS_SELECTOR, selector).get_attribute("textContent") == "All stars":
            reviews_button = driver.find_element(By.CSS_SELECTOR, selector)
            break

    if reviews_button is None:
        raise NoSuchElementException("Reviews button not found")

    # NOTE: Better to use?: ActionChains(driver).move_to_element(reviews_button).click().perform()
    reviews_button.click()

    sentiment_dropdown = find_element(driver, f"{sentiment}_reviews")
    if sentiment_dropdown is None:
        raise ValueError("Unable to find reviews dropdown")

    sentiment_dropdown.click()

    driver.refresh()  # NOTE: Prevents stale element exception

    elements = driver.find_elements(By.CSS_SELECTOR, selectors["review_elements"])
    for element in elements:
        review = {
            "asin": asin,
            "author": find_attribute(element, "review_author", "textContent"),
            "rating": find_attribute(element, "review_rating", "innerHTML"),
            "title": find_element(element, "review_title").text if find_element(element, "review_title") is not None else "",  # type: ignore
            "location_and_date": find_attribute(element, "review_date", "textContent"),
            "verified": find_attribute(element, "review_verified", "textContent"),
            "text": find_attribute(element, "review_text", "innerText"),
        }
        reviews.append(review)

    return reviews


def save_reviews(reviews: list[dict], filename: str) -> None:
    """Save reviews to a CSV file.

    Args:
        reviews (list[dict]): List of reviews.
        filename (str): Output filename.
    """
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=reviews[0].keys(), delimiter=";")
        writer.writeheader()
        writer.writerows(reviews)


# FIXME: Add `base_url` to arguments. Change `results` to list of ASINs and sort_ids.
def export_reviews(
    results: list[dict], output_directory: str, sentiment: PossibleSentiments = "all", create_empty_files: bool = True
) -> None:
    """Export reviews to CSV files.

    Args:
        results (list[dict]): List of search results.
        output_directory (str): Output directory.
        sentiment (PossibleSentiments, optional): Sentiment of the reviews. Defaults to "all".
        create_empty_files (bool, optional): Create empty files if no reviews are found. Defaults to True.

    Raises:
        ValueError: If results do not contain 'asin' and 'sort_id' keys.
    """

    # TODO: Test this
    if not all(key in results[0] for key in ["asin", "sort_id"]):
        raise ValueError("Results do not contain 'asin' and 'sort_id' keys")

    driver = webdriver.Firefox()
    for result in results:
        asin = result["asin"]
        sort_id = result["sort_id"]
        # FIXME: Use global base_url, use argument or use config. Use argument: default_base_url = "https://www.amazon.com"
        base_url = result.get("simplified_url", "https://www.amazon.com").split("/dp/")[0]
        reviews = get_reviews(driver, base_url, asin, sentiment)
        filename = f"{output_directory}/{sort_id}/{sort_id}_{sentiment}_reviews.csv"
        if not reviews:
            logger.info(f"No {sentiment} reviews found for {sort_id}. ASIN: {asin}.")
            if create_empty_files:
                logger.info(f"Creating empty file: {filename}")
                Path(filename).parent.mkdir(parents=True, exist_ok=True)
                with open(filename, "w", newline="", encoding="utf-8") as file:
                    file.write('')
            continue
        save_reviews(reviews, filename)
    driver.quit()


# def load_config(config_file: str) -> None:
#     global CONFIG
#     CONFIG = load_yaml(config_file)


# def load_selectors(config_file: str) -> None:
#     global CONFIG
#     selectors = load_yaml(config_file)
#     CONFIG = {**CONFIG, **selectors}


# @inject_config
def main(
    options: str,
    # selectors: str,
    domain: str,
    keyword: str,
    output_directory: str | None = None,
    # max_results=ConfigValue("options.max_results"),
    # max_pages=ConfigValue("options.max_search_result_pages"),
) -> None:
    # TODO: Separate options and selectors, i.e. options.yaml to CONFIG and selectors.yaml to SELECTORS
    options: dict[str, Any] = ConfigValue("options").resolve()

    base_url = f"https://www.amazon.{domain}"

    output_directory = output_directory or f"output/{keyword}_{domain}_{time.strftime('%Y%m%d')}"

    for level in options.get("log_levels", []):
        logger.add(f"{output_directory}/{level}.log", level=level.upper())

    # Scrape
    results = search_amazon(
        base_url,
        keyword,
        max_results=options.get("max_results"),
        max_search_result_pages=options.get("max_search_result_pages"),
        output_directory=output_directory,
    )

    # Add sort_title to results
    for result in results:
        result["sort_title"] = f"{result['sort_id']}_{result['title']}"
    results = [{**{"sort_title": result.pop("sort_title")}, **result} for result in results]

    save_results(results, output_directory, base_url, keyword)

    if options.get("save_images"):
        logger.info("Saving images")
        save_images_from_results(results, output_directory, subdir_key="sort_id")

    if options.get("save_description_images"):
        logger.info("Saving description images")
        save_description_images(results, output_directory, subdir_key="sort_id")

    if options.get("save_full_page_images"):
        logger.info("Saving full page images")
        driver = webdriver.Firefox()
        for result in results:
            save_webpage_as_png(
                driver, result["url"], f"{output_directory}/{result['sort_id']}/{result['sort_id']}_full_page.png"
            )
        driver.quit()

    for sentiment in options.get("export_reviews", []):
        logger.info(f"Exporting {sentiment} reviews")
        export_reviews(results, output_directory, sentiment=sentiment)

    logger.success("Scraping completed")


if __name__ == "__main__":

    main("config/options.yaml", "config/selectors.yaml", "co.uk", "juice press")
