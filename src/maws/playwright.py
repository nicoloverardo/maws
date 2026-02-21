import logging
from pathlib import Path

import httpx
from playwright.async_api import async_playwright
from pydantic import TypeAdapter
from rich.progress import track

from maws.config import Config
from maws.models import Product

logger = logging.getLogger(__name__)


async def main(
    products: Path | list[Product],
    headless: bool = True,
    output: Path | None = None,
    timeout: int = 60000,
):
    """Run the Playwright scraper to fetch detailed product information.

    Examples:
        Open a python REPL with `uv run python -m asyncio` and then run:

        >>> from pathlib import Path
        >>> from uuid import uuid4
        >>> from maws.playwright import main
        >>> import logging
        >>> from rich.logging import RichHandler
        >>> logging.basicConfig(
        ...     level=logging.INFO,
        ...     format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        ...     handlers=[RichHandler()],
        ... )
        >>> output = Path("output", str(uuid4()))
        >>> await main(Path("data/20260206_110617_products.json"), output=output)
    """
    if isinstance(products, Path):
        products = TypeAdapter(list[Product]).validate_json(
            products.read_text(encoding="utf-8")
        )
    if output is None:
        output = Path("output", "product_details")
    output.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        config = Config()
        browser = await playwright.chromium.launch(headless=headless)
        page = await browser.new_page()
        await page.goto(config.urls.base_url.encoded_string())
        logging.info("Navigated to base URL: %s", config.urls.base_url.encoded_string())
        logging.info("Username is %s", config.username)
        await page.get_by_role("link", name="Inloggen").click()
        logging.info("Login form loaded. Filling in credentials.")
        await page.get_by_role("textbox", name="E-mail").click()
        await page.get_by_role("textbox", name="E-mail").fill(config.username)
        await page.get_by_role("textbox", name="Wachtwoord").click()
        await page.get_by_role("textbox", name="Wachtwoord").fill(
            config.password.get_secret_value()
        )
        await page.get_by_role("button", name="Inloggen").click()
        logger.info("Logged in successfully.")
        await page.get_by_role("menuitem", name="Assortiment arrow_drop_down").click()
        already_downloaded_ids = [
            Path(item).name.replace(".html", "")
            for item in Path(output).glob("*.html")
            if Path(item).read_text() != ""
        ]
        to_download: list[Product] = [
            p for p in products if str(p.product_id) not in already_downloaded_ids
        ]
        logger.info(
            "Total products to download: %d (already downloaded: %d)",
            len(to_download),
            len(already_downloaded_ids),
        )
        skipped_ids = []
        for product in track(to_download, description="Downloading products"):
            try:
                logger.debug("Loading page of product %s", product.product_id)
                response = await page.goto(product.product_url.encoded_string())
                if response and response.status == httpx.codes.NOT_FOUND:
                    logger.debug(
                        "Product %s not found (404). Skipping.", product.product_id
                    )
                    skipped_ids.append(
                        {"id": product.product_id, "reason": "404 Not Found"}
                    )
                    product.exists = False
                    continue
                await page.wait_for_url(
                    product.product_url.encoded_string(), timeout=timeout
                )

                await page.wait_for_selector(
                    'div[title="Availability"]',
                    timeout=min(5000, timeout),
                    state="visible",
                )
                if await page.query_selector(".stock.available"):
                    await page.wait_for_selector(
                        "#tier-price-table tbody tr", timeout=timeout
                    )
                else:
                    logger.debug(
                        "Product %s is out of stock or not yet available. Skipping.",
                        product.product_id,
                    )
                logger.debug("Loaded. Writing page content to file.")
                Path(output, f"{product.product_id}.html").write_text(
                    await page.content(), encoding="utf-8"
                )
            except Exception as e:
                logger.debug("Failed to load product %s: %s", product.product_id, e)
                skipped_ids.append({"id": product.product_id, "reason": str(e)})
        logger.info("Finished downloading products. Skipped products: %s", skipped_ids)
        Path(output, "all_products_w_status.json").write_bytes(
            TypeAdapter(list[Product]).dump_json(products)
        )
        await browser.close()
