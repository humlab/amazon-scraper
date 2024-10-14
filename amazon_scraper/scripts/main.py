from typing import Any

import click
from loguru import logger

from amazon_scraper.configuration import ConfigStore, ConfigValue
from amazon_scraper.workflow import scrape_workflow  # type: ignore

ConfigStore.configure_context(source='config/config.yml')


@click.command()
@click.option("--domain", default=None, help="Amazon domain to scrape")
@click.option("--keyword", default=None, help="Keyword to search for")
def main(domain: str, keyword: str) -> None:
    options: dict[str, Any] = ConfigValue("options").resolve()

    domains: list[str] = [domain] if domain else ConfigValue("payload.domains").resolve()
    keywords: list[str] = [keyword] if keyword else ConfigValue("payload.keywords").resolve()

    for k in keywords:
        for d in domains:
            logger.info(f"Scraping {k} on {d}")
            scrape_workflow(options, k, d)

    logger.success("Scraping completed")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
