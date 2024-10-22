from typing import Any

import pytest

from amazon_scraper.configuration import ConfigStore, ConfigValue
from amazon_scraper.scripts.main import scrape_workflow


@pytest.mark.skip(reason="This is a debug test")
def test_scrape():
    ConfigStore.configure_context(source='config/config.yml')
    options: dict[str, Any] = ConfigValue("options").resolve()
    domain = "de"
    keyword = "prayer shawl"
    scrape_workflow(options, keyword, domain, force=True)
    assert True
