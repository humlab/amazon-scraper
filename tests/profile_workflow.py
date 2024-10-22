from typing import Any

from amazon_scraper.configuration import ConfigStore, ConfigValue  # type: ignore[attr-defined]
from amazon_scraper.scripts.main import scrape_workflow

ConfigStore.configure_context(source='tests/profile_config.yml')
options: dict[str, Any] = ConfigValue("options").resolve()
domain = "de"
keyword = "laptop"
scrape_workflow(options, keyword, domain, force=True)
