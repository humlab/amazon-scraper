import time
from typing import Any

import click
from loguru import logger

from amazon_scraper import (
    export_reviews,
    get_driver,
    save_description_images,
    save_images_from_results,
    save_results,
    save_webpage_as_png,
    search_amazon,
)
from configuration import ConfigStore, ConfigValue  # type: ignore

ConfigStore.configure_context(source='config/config.yml')


def scrape_workflow(options: dict[str, Any], keyword, domain) -> None:

    base_url: str = f"https://www.amazon.{domain}"
    target_root: str = ConfigValue("payload.target_folder", mandatory=True).resolve()

    output_directory: str = f"{target_root}/{keyword}_{domain}_{time.strftime('%Y%m%d')}"

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
        driver = get_driver()
        for result in results:
            try:
                target_filename: str = f"{output_directory}/{result['sort_id']}/{result['sort_id']}_full_page.png"
                save_webpage_as_png(driver, result["url"], target_filename)
            except Exception as e:
                logger.error(f"Error saving full page image to {target_filename}: {e}")
                continue
        driver.quit()

    for sentiment in options.get("export_reviews", []):
        logger.info(f"Exporting {sentiment} reviews")
        export_reviews(results, output_directory, sentiment=sentiment)


@click.command()
@click.option("--domain", default=None, help="Amazon domain to scrape")
@click.option("--keyword", default=None, help="Keyword to search for")
def main(domain: str, keyword: str) -> None:
    options: dict[str, Any] = ConfigValue("options").resolve()

    domains: list[str] = [domain] if domain else ConfigValue("payload.domains").resolve()
    keywords: list[str] = [keyword] if keyword else ConfigValue("payload.keywords").resolve()

    for domain in domains:
        for keyword in keywords:
            logger.info(f"Scraping {keyword} on {domain}")
            scrape_workflow(options, keyword, domain)

    logger.success("Scraping completed")


if __name__ == "__main__":

    main()
