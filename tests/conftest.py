from typing import Any, Generator

import pytest
from _pytest.logging import LogCaptureFixture
from loguru import logger

from amazon_scraper.configuration.inject import ConfigStore  # type: ignore

ConfigStore.configure_context(source='tests/config.yml')


@pytest.fixture(name="caplog")
def caplog_fixture(caplog: LogCaptureFixture) -> Generator[Any, Any, Any]:
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
