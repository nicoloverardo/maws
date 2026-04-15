import asyncio
import logging
from pathlib import Path

import httpx
from playwright.async_api import async_playwright
from playwright_stealth.stealth import Stealth

from maws.goa.config import Config
from maws.goa.parser import MenuParser, PaginationParser

logger = logging.getLogger(__name__)


class GoaAsyncClient:
    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self.rate_limiter = asyncio.Semaphore(1)

    def extract_menu_links(self, html: str) -> list[str]:
        parser = MenuParser()
        parser.feed(html)
        return parser.hrefs

    def extract_total_pages(self, html: str) -> int:
        parser = PaginationParser()
        parser.feed(html)

        if not parser.pages:
            return 1

        return max(parser.pages)

    async def fetch(
        self, client: httpx.AsyncClient, url: str, sleep: bool = True
    ) -> httpx.Response:
        async with self.rate_limiter:
            response = await client.get(
                url, headers=self.config.user_agents.get_random_ua_header()
            )
            response.raise_for_status()
            if sleep:
                await asyncio.sleep(self.config.urls.rate_limit_seconds)
            return response

    async def parse_all_with_playwright(
        self,
        headless: bool = True,
        output: Path | None = None,
        timeout: int = 60000,
    ):
        """Run the Playwright scraper to fetch all products information."""
        if output is None:
            output = Path("output", "goa", "product_details")
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)
        async with Stealth().use_async(async_playwright()) as playwright:
            config = Config()
            browser = await playwright.chromium.launch(headless=headless, slow_mo=1000)
            page = await browser.new_page(user_agent=config.user_agents.get_random_ua())
            await page.goto(
                config.urls.base_url.encoded_string(), wait_until="networkidle"
            )
            logging.info(
                "Navigated to base URL: %s", config.urls.base_url.encoded_string()
            )
            content = await page.content()
            links = self.extract_menu_links(content)
            logger.info("Extracted %d menu links", len(links))

            for link in links:
                logger.info("Processing link: %s", link)
                await page.goto(link)
                content = await page.content()
                total_pages = self.extract_total_pages(content)
                logger.info("Total pages for %s: %d", link, total_pages)

                for page_num in range(1, total_pages + 1):
                    page_url = f"{link}?page={page_num}"
                    logger.info("Fetching page URL: %s", page_url)
                    await page.goto(page_url)
                    content = await page.content()
                    logger.debug("Loaded. Writing page content to file.")
                    Path(
                        output,
                        f"{link.replace(self.config.urls.base_url.encoded_string(), '')}_page_{page_num}.html",
                    ).write_text(content, encoding="utf-8")

            await browser.close()
