from typing import Any, Generator

import pytest
from _pytest.logging import LogCaptureFixture
from loguru import logger
from selenium import webdriver

from amazon_scraper.configuration.inject import ConfigStore  # type: ignore

ConfigStore.configure_context(source='tests/config.yml')


@pytest.fixture(name="caplog")
def fixture_caplog(caplog: LogCaptureFixture) -> Generator[Any, Any, Any]:
    """See: https://loguru.readthedocs.io/en/stable/resources/migration.html#replacing-caplog-fixture-from-pytest-library"""
    handler_id = logger.add(
        caplog.handler,
        format="{message}",
        level=0,
        filter=lambda record: record["level"].no >= caplog.handler.level,
        enqueue=False,  # Set to 'True' if your test is spawning child processes.
    )
    yield caplog
    logger.remove(handler_id)


@pytest.fixture(name="driver")
def fixture_driver():
    """Fixture for Selenium WebDriver.

    Yields:
        selenium.webdriver.Firefox: An instance of Firefox WebDriver.
    """
    options = webdriver.FirefoxOptions()
    options.add_argument('-headless')

    options.set_preference("network.dns.disableIPv6", True)  # Disable IPv6 if DNS issues occur
    options.set_preference("network.http.connection-timeout", 10)  # Set connection timeout
    options.set_preference("network.http.response-timeout", 10)  # Set response timeout

    executable_path = "/snap/bin/firefox.geckodriver"  # FIXME: This is a hardcoded path. It should be dynamic. Use `webdriver_manager` package.
    service = webdriver.FirefoxService(executable_path=executable_path)
    driver = webdriver.Firefox(service=service, options=options)
    yield driver
    driver.quit()
