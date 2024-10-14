import time
from typing import Any

from loguru import logger
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait

from amazon_scraper.configuration import ConfigValue  # type: ignore
from amazon_scraper.utility import retry  # type: ignore


def get_driver() -> WebDriver:
    options = webdriver.FirefoxOptions()
    options.add_argument('-headless')
    driver = webdriver.Firefox(options=options)
    return driver


def find_webdriver_parent(item: WebDriver | WebElement, depth: int = 0) -> WebDriver | None:
    """Find the parent webdriver object. This function is recursive. The depth parameter is used to prevent infinite recursion.

    Args:
        item (WebDriver | WebElement): Webdriver object.
        depth (int, optional): Recursion depth. Defaults to 0.

    Returns:
        WebDriver | None: Parent webdriver object. None if not found.
    """
    if depth > 10:  # FIXME: Handle infinite recursion better
        return None
    if isinstance(item, WebDriver):
        return item
    if hasattr(item, 'parent'):
        return find_webdriver_parent(item.parent, depth + 1)
    return None


def wait_page_ready(item: WebDriver | WebElement) -> None:
    """Wait for the page to load.

    Args:
        item (WebDriver | WebElement): Webdriver object.

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


def find_element(item: WebDriver | WebElement, key: str, *, by: str = By.CSS_SELECTOR) -> WebElement | None:
    """Find an element using a key from the selectors.yaml file. The key is used to get a CSS selector or a list of CSS selectors from the selectors.yaml file. The function tries each selector until it finds an element. If no element is found, it returns None.

    Args:
        item (WebDriver | WebElement): A Selenium WebDriver instance or a WebElement.
        key (str): Key from the selectors.yaml file.
        by (str, optional): Selenium By method. Defaults to By.CSS_SELECTOR.

    Returns:
        WebElement | None: A Selenium WebElement or None.
    """
    config: dict[str, Any] = ConfigValue(f"selectors.{key}").resolve()
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


def wait_element(item: WebDriver | WebElement, key: str, *, by: str = By.CSS_SELECTOR, timeout: int = 30) -> None:
    """Wait for an element to appear on the page. The function tries each selector until it finds an element. If no element is found after the timeout, it raises a NoSuchElementException.

    Args:
        item (WebDriver | WebElement): A Selenium WebDriver instance or a WebElement.
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
    item: WebDriver | WebElement,
    key: str,
    attribute: str,
    *,
    by: str = By.CSS_SELECTOR,
    default: Any = None,
) -> Any:
    """Find an attribute of an element using a key from the selectors.yaml file. The key is used to get a CSS selector or a list of CSS selectors from the selectors.yaml file. The function tries each selector until it finds an element. If no element is found, it returns the default value.

    Args:
        item (WebDriver | WebElement): A Selenium WebDriver instance or a WebElement.
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


def reject_cookies(driver: WebDriver) -> None:
    """Attempts to find and click a button on a web page to reject cookies using Selenium WebDriver. If the button is found, it clicks the button; otherwise, it does nothing.

    Args:
        driver (WebDriver): A Selenium WebDriver instance.
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


def dismiss_popup(driver: WebDriver, keyword: str) -> None:
    """Attempts to find and click a button on a web page to dismiss a popup using Selenium WebDriver. If the button is found, it clicks the button; otherwise, it does nothing.

    Args:
        driver (WebDriver): A Selenium WebDriver instance.
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


def accept_cookies(driver: WebDriver) -> None:
    """Attempts to find and click a button on a web page to accept cookies using Selenium WebDriver. If the button is found, it clicks the button; otherwise, it does nothing.

    Args:
        driver (WebDriver): _description_
    """
    cookies_button = find_element(driver, "accept_cookies")
    if cookies_button is not None:
        cookies_button.click()
