# pylint: disable=broad-exception-caught
import csv
import time
from pathlib import Path
from typing import Any, Literal, Sequence
from urllib.parse import urlparse

import requests
from loguru import logger
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait

from amazon_scraper import scrape_utility as su
from amazon_scraper.configuration import ConfigValue  # type: ignore


def get_search_result_pages(
    driver: WebDriver, url: str, keyword: str, max_search_result_pages: int | None = None
) -> list[str]:
    """Get search result pages from a search engine. The function searches for a keyword and returns a list of search result pages. If the maximum number of search result pages is set, the function returns the specified number of pages. If the search box is not found, the function raises a NoSuchElementException. If the number of pages is 0, the function logs a warning. If only one page is found, the function logs an info message and returns a list with one page, the current URL.

    Args:
        driver (WebDriver): A Selenium WebDriver instance.
        url (str): URL of the search engine.
        keyword (str): Search keyword.
        max_search_result_pages (int | None, optional): Maximum number of search result pages. Defaults to None.

    Raises:
        NoSuchElementException: If the search box is not found.

    Returns:
        list[str]: List of search result pages.
    """
    driver.get(url)

    su.wait_element(driver, "search_box")

    search_box = su.find_element(driver, "search_box")
    if not search_box:
        raise NoSuchElementException("Search box not found")
    search_box.send_keys(keyword)
    search_box.send_keys(Keys.RETURN)

    su.wait_page_ready(driver)
    su.reject_cookies(driver)

    try:
        su.wait_element(driver, "number_of_pages")
        number_of_pages = int(su.find_attribute(driver, "number_of_pages", "textContent", default='1'))
        logger.info(f"Found {number_of_pages} pages")
        number_of_pages = min(number_of_pages, max_search_result_pages) if max_search_result_pages else number_of_pages
        logger.info(f"Max search result pages set to {max_search_result_pages}. Returning {number_of_pages} pages")

        pages: list[str] = (
            [driver.current_url]
            + [
                f"{driver.current_url.replace('nb_sb_noss', f'sr_pg_{p}')}&page={p+1}"
                for p in range(1, number_of_pages)
            ]
            if number_of_pages > 1
            else [driver.current_url]
        )
    except NoSuchElementException:
        logger.info("Found only one page.")
        pages = [driver.current_url]
    except Exception as e:
        logger.exception(f"Error getting search result pages: {e}")
        pages = [driver.current_url]
    return pages


def get_products(driver: WebDriver, page: str, base_url: str, filename: str) -> list[dict[str, Any]]:
    """Get products from a search result page.

    Args:
        driver (WebDriver): A Selenium WebDriver instance.
        page (str): URL of the search result page.
        base_url (str): Base URL of the search engine.
        filename (str): Output filename.

    Returns:
        list[dict[str, Any]]: List of products found on the page. Each product is a dictionary with keys 'title', 'price', 'url', 'asin', 'simplified_url', and 'is_sponsored'.
    """
    selectors: dict[str, Any] = ConfigValue("selectors").resolve()

    driver.get(page)
    su.wait_page_ready(driver)

    save_webpage_as_png(driver, page, filename)

    elements: list[WebElement] = driver.find_elements(By.CSS_SELECTOR, selectors["products"])

    products: list[dict[str, Any]] = []

    for element in elements:
        try:
            product = {
                "title": su.find_attribute(element, "product_title", "textContent"),
                "price": su.find_attribute(element, "product_price", "innerText"),  # 'textContent'
                "url": su.find_attribute(element, "product_url", "href"),
                "asin": (asin := element.get_attribute("data-asin")),
                "simplified_url": f"{base_url}/dp/{asin}",
                "is_sponsored": bool(su.find_attribute(element, "sponsored", "innerText")),
            }

            products.append(product)
        except NoSuchElementException as e:
            logger.exception(f"Error processing product: {e}")
            continue

    logger.info(f"Processed {len(products)} products on page {page}")

    return products


def get_image_urls(driver: WebDriver, url: str | None = None) -> Sequence[str | None]:
    """Get image links from an Amazon product page.

    Args:
        driver (WebDriver): A Selenium WebDriver instance.
        url (str): URL of the Amazon product page.

    Returns:
        Sequence[str | None]: A sequence of image links (URLs).
    """
    image_urls: list[str] = []
    try:
        if url:
            driver.get(url)
            su.wait_page_ready(driver)

        if driver.current_url == "about:blank":
            raise ValueError("No URL provided")

        if "www.amazon" not in driver.current_url:
            raise ValueError(f"Not an Amazon product page: {driver.current_url}")

        su.wait_page_ready(driver)

        elements = driver.find_elements(By.CSS_SELECTOR, "#altImages > ul > li")
        elements = [element for element in elements if element.size["height"] != 0]

        actions = ActionChains(driver)

        for element in elements:
            driver.execute_script("arguments[0].scrollIntoView();", element)  # type: ignore[no-untyped-call]
            actions.move_to_element(element).perform()
            time.sleep(1)

        images = driver.find_element(By.CSS_SELECTOR, "#main-image-container").find_elements(By.TAG_NAME, "img")
        for image in images:
            if image.get_attribute("data-old-hires"):
                image_urls.append(str(image.get_attribute("data-old-hires")))
            else:
                src: str | None = image.get_attribute("src")
                if src and not src.endswith("gif"):
                    image_urls.append(src)
    except TimeoutError as e:
        logger.exception(f"Timeout error: {e}")
    except Exception as e:
        logger.exception(f"Error getting image URLs: {e}")

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
        try:
            response: requests.Response = requests.get(image_link, timeout=5)
            file_extension: str = Path(image_link).suffix[1:]
            with open(f"{directory}/{filename}.{file_extension}", "wb") as file:
                file.write(response.content)
        except Exception as e:
            logger.exception(f"Error saving image {image_link} to {directory}/{filename}: {e}")


def get_product_info(driver: WebDriver, url: str) -> dict[str, Any]:
    """Get product information from an Amazon product page.

    Args:
        driver (WebDriver): A Selenium WebDriver instance.
        url (str): URL of the Amazon product page.

    Returns:
        dict[str, Any]: Product information.
    """
    for _ in range(3):
        try:
            driver.get(url)

            su.wait_page_ready(driver)

            title = su.find_attribute(driver, "title", "innerText")
            price = su.find_attribute(driver, "price", "innerText")
            image_link = su.find_attribute(driver, "image", "src")
            about = su.find_attribute(driver, "about", "innerText", default="").strip()

            product_description = su.find_attribute(
                driver, "description", "innerText", default="IMAGE_DESCRIPTION_ONLY"
            ).strip()

            # FIXME: Check if there are images in the product description
            if su.find_element(driver, "description"):
                description_image_urls = [
                    image.get_attribute("src")
                    for image in su.find_element(driver, "description").find_elements(By.TAG_NAME, "img")  # type: ignore
                    if not image.get_attribute("src").endswith("gif")  # type: ignore
                ]
            else:
                description_image_urls = []

            details = su.find_attribute(driver, "details", "innerText", default="")
            product_details = {
                key: value
                for line in details.split("\n")
                if (parts := line.split('\t', 1)) and len(parts) == 2
                for key, value in [parts]
            }

            rating = su.find_attribute(driver, "rating", "innerText", default="").strip()
            number_of_ratings = su.find_attribute(driver, "number_of_ratings", "innerText", default="")
            number_of_ratings = "".join([c for c in number_of_ratings if c.isdigit()])

            store = su.find_attribute(driver, "store", "innerText", default="")
            # FIXME: Fix for other domains (e.g. amazon.de, amazon.se). Add to config.
            store = (
                store.replace("Visit the ", "")
                .replace("Brand: ", "")
                .replace(" Store", "")
                .replace(" Brand", "")
                .strip()
            )

            store_url = su.find_attribute(driver, "store", "href")

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
        except TimeoutError as e:
            logger.exception(f"Timeout error: {e}")
            time.sleep(30)
            continue
        except Exception as e:
            logger.exception(f"Error getting product information: {e}")
            return {}

    return {}


def get_product_info_by_asin(driver: WebDriver | None = None, *, base_url: str, asin: str) -> dict[str, Any]:
    """Get product information from an Amazon product page using the ASIN.

    Args:
        base_url (str): Base URL of the search engine.
        asin (str): Amazon Standard Identification Number (ASIN).
        driver (WebDriver | None, optional): A Selenium WebDriver instance. Defaults to None.

    Returns:
        dict[str, Any]: Product information.
    """
    if driver is None:
        driver = su.get_driver()
    url = f"{base_url}/dp/{asin}"
    return get_product_info(driver, url)


def save_results(results: list[dict[str, Any]], directory: str, base_url: str, keyword: str) -> None:
    """Save results to a CSV file.

    Args:
        results (list[dict[str, Any]]): List of search results.
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


def save_webpage_as_png(driver: WebDriver | None, url: str, filename: str) -> None:
    """Save a webpage as a PNG file.

    Args:
        driver (WebDriver | None): A Selenium WebDriver instance. Defaults to None.
        url (str): URL of the webpage.
        filename (str): Output filename.

    Raises:
        Exception: If an error occurs while saving the webpage as a PNG file.
    """
    try:

        if driver is None:
            driver = su.get_driver()
        driver.get(url)

        WebDriverWait(driver, 30).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"  # type: ignore[no-untyped-call]
        )

        su.reject_cookies(driver)
        su.dismiss_popup(driver, "dismiss_delivery_options")

        width = driver.execute_script(
            "return Math.max( document.body.scrollWidth, document.body.offsetWidth, document.documentElement.clientWidth, document.documentElement.scrollWidth, document.documentElement.offsetWidth );"
        )  # type: ignore[no-untyped-call]

        height = driver.execute_script(
            "return Math.max( document.body.scrollHeight, document.body.offsetHeight, document.documentElement.clientHeight, document.documentElement.scrollHeight, document.documentElement.offsetHeight );"
        )  # type: ignore[no-untyped-call]

        driver.set_window_size(width, height)

        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        driver.save_screenshot(filename)
    except Exception as e:
        logger.exception(f"Error saving webpage {url} as PNG: {e}")


def save_full_page_screenshots(output_directory: str, results: list[dict[str, Any]]) -> None:
    """Save full page screenshots of search results to a directory.

    Args:
        output_directory (str): Output directory.
        results (list[dict[str, Any]]): List of search results.
    """
    try:
        driver: WebDriver = su.get_driver()
        for result in results:
            target_filename: str = f"{output_directory}/{result['sort_id']}/{result['sort_id']}_full_page.png"
            save_webpage_as_png(driver, result["url"], target_filename)
        driver.quit()
    except Exception as e:
        logger.exception(f"Error saving full page screenshots: {e}")


def search_amazon(
    base_url: str,
    keyword: str,
    max_results: int | None = None,
    max_search_result_pages: int | None = None,
    output_directory: str | None = None,
) -> list[dict[str, Any]]:
    """Search Amazon for a keyword and get product information. Optionally, if an output directory is provided, save search result pages as PNG files.

    Args:
        base_url (str): Base URL of the search engine.
        keyword (str): The search keyword.
        max_results (int | None, optional): Maximum number of results. Defaults to None.
        max_search_result_pages (int | None, optional): Maximum number of search result pages. Defaults to None.
        output_directory (str | None, optional): Output directory. If provided, save search result pages as PNG files. Defaults to None.

    Returns:
        list[dict[str, Any]]: List of search results.
    """
    logger.info(f"Searching for {keyword} on {base_url}")

    driver: WebDriver = su.get_driver()

    products: list[dict[str, Any]] = []
    try:
        pages: list[str] = get_search_result_pages(driver, base_url, keyword, max_search_result_pages)

        candidates: list[dict[str, Any]] = get_products_found_on_pages(
            driver, base_url, max_results, pages, output_directory
        )

        products = get_product_informations(driver, base_url, keyword, candidates)

    except NoSuchElementException as e:
        logger.exception(f"Error searching for {keyword}: {e}")
        products = []
    except Exception as e:
        logger.exception(f"Error searching for {keyword}: {e}")
        products = []
    finally:
        driver.quit()

    return products


def store_search_result_images(driver: WebDriver, output_directory: str | None, pages: list[str]) -> None:
    """Store search result images as PNG files.

    Args:
        driver (WebDriver): A Selenium WebDriver instance.
        output_directory (str | None): Output directory.
        pages (list[str]): List of search result pages.
    """
    if not output_directory:
        return
    for index, page in enumerate(pages, start=1):
        save_webpage_as_png(driver, page, f"{output_directory}/search_page_{str(index).zfill(2)}.png")


def get_product_informations(
    driver: WebDriver, base_url: str, keyword: str, candidates: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Get product information from a list of search results.

    Args:
        driver (WebDriver): A Selenium WebDriver instance.
        base_url (str): Base URL of the search engine.
        keyword (str): The search keyword.
        candidates (list[dict[str, Any]]): List of search results.

    Returns:
        list[dict[str, Any]]: List of search results with product information.
    """

    def get_image_names(urls: list[str], sort_id: str) -> list[str]:
        return [f"{sort_id}{chr(97+index)}.{url.split('.')[-1]}" for index, url in enumerate(urls)]

    sort_id = 1
    products: list[dict[str, Any]] = []
    for candidate in candidates:
        try:
            product_info: dict[str, Any] = get_product_info(driver, candidate["url"])

            if not product_info:
                continue

            sort_id_str: str = str(sort_id).zfill(4)
            candidate.update(
                product_info
                | {
                    "tld": urlparse(base_url).netloc.split('.')[-1],
                    "keyword": keyword,
                    "sort_id": sort_id_str,
                    "image_names": get_image_names(product_info.get("image_urls", []), sort_id_str),
                    "sort_title": f"{sort_id_str}_{product_info.get('title_info', '???')}",
                }
            )

            products.append(candidate)
            sort_id += 1

        except Exception as e:
            logger.exception(f"Error processing product {candidate['url']}: {e}")
            continue

    return products


def get_products_found_on_pages(
    driver: WebDriver, base_url: str, max_results: int | None, pages: list[str], output_directory: str | None = None
) -> list[dict[str, Any]]:
    """Get products found on a list of search result pages.

    Args:
        driver (WebDriver): A Selenium WebDriver instance.
        base_url (str): Base URL of the search engine.
        max_results (int | None): Maximum number of results to return. Defaults to None.
        pages (list[str]): List of search result pages.
        output_directory (str | None, optional): Output directory. Defaults to None.

    Returns:
        list[dict[str, Any]]: List of products found on the pages.
    """
    candidates: list[dict[str, Any]] = []
    for i, page in enumerate(pages, start=1):
        try:
            filename = f"{output_directory}/search_page_{str(i).zfill(2)}.png"
            candidates += get_products(driver, page, base_url, filename)
            if max_results and len(candidates) >= max_results:
                logger.info(f"Found {max_results} results. Stopping search.")
                break
        except Exception as e:
            logger.exception(f"skipped: error processing page {page}: {e}")
            continue

    if max_results:
        candidates = candidates[:max_results]

    return candidates


def save_images_from_results(results: list[dict[str, Any]], directory: str, subdir_key: str) -> None:
    """Save images from a list of search results to a directory. The subdirectory is created using a key from the results.

    Args:
        results (list[dict[str, Any]]): List of search results.
        directory (str): Output directory.
        subdir_key (str): Key to use as subdirectory.
    """
    for result in results:
        subdirectory = result[subdir_key]
        result_directory: str = f"{directory}/{subdirectory}"
        save_images(result["image_urls"], result["image_names"], result_directory)


def save_description_images(results: list[dict[str, Any]], directory: str, subdir_key: str) -> None:
    """Save description images from a list of search results to a directory. The subdirectory is created using a key from the results.

    Args:
        results (list[dict[str, Any]]): List of search results.
        directory (str): Output directory.
        subdir_key (str): Key to use as subdirectory.
    """
    for result in results:
        try:
            subdirectory: str = result[subdir_key]
            if description_image_urls := result.get("description_image_urls"):
                description_image_names: list[str] = [
                    f"{result['sort_id']}_product_image_{str(i+1).zfill(2)}" for i in range(len(description_image_urls))
                ]
                save_images(description_image_urls, description_image_names, f"{directory}/{subdirectory}")
        except Exception as e:
            logger.exception(f"Error saving description images: {e}")
            continue


PossibleSentiments = Literal["1_star", "2_star", "3_star", "4_star", "5_star", "positive", "critical", "all"]


def get_reviews(
    driver: WebDriver,
    base_url: str,
    asin: str,
    sentiment: PossibleSentiments,
) -> list[dict[str, Any]] | None:
    """Get reviews from an Amazon product page.

    Args:
        driver (WebDriver): A Selenium WebDriver instance.
        base_url (str): Base URL of the search engine.
        asin (str): Amazon Standard Identification Number (ASIN).
        sentiment (PossibleSentiments): Sentiment of the reviews.

    Raises:
        ValueError: If the reviews button is not found.

    Returns:
        list[dict] | None: List of reviews or None.
    """
    selectors: dict[str, Any] = ConfigValue("selectors").resolve()

    url: str = f"{base_url}/product-reviews/{asin}"
    driver.get(url)

    su.wait_page_ready(driver)
    su.reject_cookies(driver)
    su.dismiss_popup(driver, "dismiss_delivery_options")

    reviews = []

    # TODO: Add function get_element_with_attribute_value
    reviews_button: WebElement | None = None
    try:
        for selector in selectors.get("reviews_stars_button", []):
            if driver.find_element(By.CSS_SELECTOR, selector).get_attribute("textContent") == "All stars":
                reviews_button = driver.find_element(By.CSS_SELECTOR, selector)
                break
    except NoSuchElementException:
        logger.warning(f"Reviews button not found for ASIN: {asin}")
        return None

    # NOTE: Better to use?: ActionChains(driver).move_to_element(reviews_button).click().perform()
    if reviews_button is not None:
        reviews_button.click()

    sentiment_dropdown = su.find_element(driver, f"{sentiment}_reviews")
    if sentiment_dropdown is None:
        logger.warning(f"Unable to find reviews dropdown for ASIN: {asin} and sentiment: {sentiment}")
        return None

    sentiment_dropdown.click()

    driver.refresh()  # NOTE: Prevents stale element exception

    elements = driver.find_elements(By.CSS_SELECTOR, selectors["review_elements"])
    for element in elements:
        review = {
            "asin": asin,
            "author": su.find_attribute(element, "review_author", "textContent"),
            "rating": su.find_attribute(element, "review_rating", "innerHTML"),
            "title": su.find_element(element, "review_title").text if su.find_element(element, "review_title") is not None else "",  # type: ignore
            "location_and_date": su.find_attribute(element, "review_date", "textContent"),
            "verified": su.find_attribute(element, "review_verified", "textContent"),
            "text": su.find_attribute(element, "review_text", "innerText"),
        }
        reviews.append(review)

    return reviews


def save_reviews(reviews: list[dict[str, Any]], filename: str) -> None:
    """Save reviews to a CSV file.

    Args:
        reviews (list[dict[str, Any]]): List of reviews.
        filename (str): Output filename.
    """
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=reviews[0].keys(), delimiter=";")
        writer.writeheader()
        writer.writerows(reviews)


# FIXME: Add `base_url` to arguments. Change `results` to list of ASINs and sort_ids.
def export_reviews(
    results: list[dict[str, Any]],
    output_directory: str,
    sentiment: PossibleSentiments = "all",
    create_empty_files: bool = True,
) -> None:
    """Export reviews to CSV files.

    Args:
        results (list[dict[str, Any]]): List of search results.
        output_directory (str): Output directory.
        sentiment (PossibleSentiments, optional): Sentiment of the reviews. Defaults to "all".
        create_empty_files (bool, optional): Create empty files if no reviews are found. Defaults to True.

    Raises:
        ValueError: If results do not contain 'asin' and 'sort_id' keys.
    """

    # TODO: Test this
    if not all(key in results[0] for key in ["asin", "sort_id"]):
        raise ValueError("Results do not contain 'asin' and 'sort_id' keys")

    driver: WebDriver = su.get_driver()
    try:
        for result in results:
            asin = result["asin"]
            sort_id = result["sort_id"]
            # FIXME: Use global base_url, use argument or use config. Use argument: default_base_url = "https://www.amazon.com"
            base_url = result.get("simplified_url", "https://www.amazon.com").split("/dp/")[0]
            reviews = get_reviews(driver, base_url, asin, sentiment)
            filename: str = f"{output_directory}/{sort_id}/{sort_id}_{sentiment}_reviews.csv"
            if not reviews:
                logger.info(f"No {sentiment} reviews found for {sort_id}. ASIN: {asin}.")
                if create_empty_files:
                    logger.info(f"Creating empty file: {filename}")
                    Path(filename).parent.mkdir(parents=True, exist_ok=True)
                    with open(filename, "w", newline="", encoding="utf-8") as file:
                        file.write('')
                continue
            save_reviews(reviews, filename)
    except Exception as e:
        logger.exception(f"Error exporting reviews: {e}")
    finally:
        driver.quit()
