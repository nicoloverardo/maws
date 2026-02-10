import logging
from pathlib import Path

from playwright.async_api import async_playwright
from pydantic import TypeAdapter

from maws.config import Config
from maws.models import Product

logger = logging.getLogger(__name__)


async def main(
    products: Path | list[Product], headless: bool = True, output: Path | None = None
):
    """Run the Playwright scraper to fetch detailed product information.

    Examples:
        Open a python REPL with `uv run python -m asyncio` and then run:

        >>> await main(Path("output/20260206_110617_products.json"))
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
        await page.get_by_role("link", name="Inloggen").click()
        await page.get_by_role("textbox", name="E-mail").click()
        await page.get_by_role("textbox", name="E-mail").fill(config.username)
        await page.get_by_role("textbox", name="Wachtwoord").click()
        await page.get_by_role("textbox", name="Wachtwoord").fill(
            config.password.get_secret_value()
        )
        await page.get_by_role("button", name="Inloggen").click()
        logger.info("Logged in successfully.")
        await page.get_by_role("menuitem", name="Assortiment arrow_drop_down").click()
        for product in products:
            logger.info("Loading page of product %s", product.product_id)
            await page.goto(product.product_url.encoded_string())
            await page.wait_for_url(product.product_url.encoded_string(), timeout=60000)
            logger.info("Loaded. Writing page content to file.")
            Path(output, f"{product.product_id}.html").write_text(
                await page.content(), encoding="utf-8"
            )
        await browser.close()
