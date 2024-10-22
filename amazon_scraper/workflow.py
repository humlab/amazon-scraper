import glob
import shutil
import time
from typing import Any

from loguru import logger

from amazon_scraper.amazon_scraper import (
    export_reviews,
    save_description_images,
    save_full_page_screenshots,
    save_images_from_results,
    save_results,
    search_amazon,
)
from amazon_scraper.configuration.inject import ConfigValue


def scrape_workflow(options: dict[str, Any], keyword: str, domain: str, force: bool = False) -> None:

    base_url: str = f"https://www.amazon.{domain}"
    target_root: str = ConfigValue("payload.target_folder", mandatory=True).resolve()

    for folder in glob.glob(f"{target_root}/{keyword}_{domain}_*"):
        if force:
            logger.info(f"Force scraping {keyword} on {domain}: removing {folder}")
            shutil.rmtree(folder, ignore_errors=True)
        else:
            logger.info(f"Skipping {keyword} on {domain} as it has already been scraped")
            return

    output_directory: str = f"{target_root}/{keyword}_{domain}_{time.strftime('%Y%m%d')}"

    logger_ids: set[int] = set()
    for level in options.get("log_levels", []):
        logger_ids.add(logger.add(f"{output_directory}/{level}.log", level=level.upper()))

    try:
        # Scrape
        results = search_amazon(
            base_url,
            keyword,
            max_results=options.get("max_results"),
            max_search_result_pages=options.get("max_search_result_pages"),
            output_directory=output_directory,
        )

        if len(results) == 0:
            logger.warning(f"No results found for {keyword} on {domain}")
            return

        save_results(results, output_directory, base_url, keyword)

        if options.get("save_images"):
            logger.info("Saving images")
            save_images_from_results(results, output_directory, subdir_key="sort_id")

        if options.get("save_description_images"):
            logger.info("Saving description images")
            save_description_images(results, output_directory, subdir_key="sort_id")

        if options.get("save_full_page_images"):
            logger.info("Saving full page images")
            save_full_page_screenshots(output_directory, results)

        for sentiment in options.get("export_reviews", []):
            logger.info(f"Exporting {sentiment} reviews")
            export_reviews(results, output_directory, sentiment=sentiment)

        logger.success(f"Finished scraping {keyword} on {domain}")

    except Exception as e:  # pylint: disable=broad-except
        logger.exception(f"ABORTED Error scraping {keyword} on {domain}: {e}")

    finally:
        for logger_id in logger_ids:
            logger.remove(logger_id)
