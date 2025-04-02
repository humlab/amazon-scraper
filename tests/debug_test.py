from typing import Any

import pytest

from amazon_scraper.configuration import ConfigStore, ConfigValue  # type: ignore[attr-defined]
from amazon_scraper.workflow import scrape_workflow


@pytest.mark.skip(reason="This is a debug test")
def test_scrape():
    ConfigStore.configure_context(source='config/config.yml')
    options: dict[str, Any] = ConfigValue("options").resolve()
    options["max_results"] = 1
    options["max_search_result_pages"] = 1
    domain = "de"
    keyword = "prayer shawl"
    scrape_workflow(options, keyword, domain, force=True)
    assert True
