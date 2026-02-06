import asyncio
import logging
import math
from pathlib import Path

import httpx
from pydantic import TypeAdapter

from maws.config import Config
from maws.models import Product
from maws.parser import ProductHTMLParser

logger = logging.getLogger(__name__)


class MawsAsyncClient:
    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self.rate_limiter = asyncio.Semaphore(1)

    def _parse_products_from_html(self, data: httpx.Response | str) -> list[Product]:
        html = data.text if isinstance(data, httpx.Response) else data

        parser = ProductHTMLParser()
        parser.feed(html)
        products = [Product(**p) for p in parser.products]
        return products

    def parse_folder(
        self, folder: str | Path, output_json: str | Path | None = None
    ) -> list[Product]:
        folder = Path(folder)
        all_products: list[Product] = []

        for file in folder.glob("page_*.html"):
            logger.info("Parsing products from '%s'…", file)
            html = file.read_text(encoding="utf-8")
            products = self._parse_products_from_html(html)
            all_products.extend(products)

        logger.info("Total products parsed: %d", len(all_products))

        if output_json is not None:
            output_json = Path(output_json)
            output_json.parent.mkdir(exist_ok=True, parents=True)
            logger.info("Saving parsed products to '%s'…", output_json)
            Path(output_json).write_bytes(
                TypeAdapter(list[Product]).dump_json(all_products)
            )

        return all_products

    async def fetch(self, client: httpx.AsyncClient, url: str) -> httpx.Response:
        async with self.rate_limiter:
            response = await client.get(
                url, headers=self.config.user_agents.get_random_ua_header()
            )
            response.raise_for_status()
            await asyncio.sleep(self.config.urls.rate_limit_seconds)
            return response

    async def login(self, client: httpx.AsyncClient):
        response = await client.post(
            self.config.urls.login_url,
            json={
                "username": self.config.username,
                "password": self.config.password.get_secret_value(),
                "captcha_form_id": "user_login",
                "context": "checkout",
            },
            follow_redirects=True,
        )
        response.raise_for_status()

    async def download_all_products(
        self, output: str | Path = "output", max_pages: int | None = None, skip: int = 0
    ) -> Path:
        Path(output).mkdir(exist_ok=True, parents=True)

        async with httpx.AsyncClient(timeout=self.config.urls.timeout) as client:
            logger.info("Fetch website for the first time")
            await self.fetch(client, self.config.urls.base_url.encoded_string())

            if self.config.username is not None and self.config.password is not None:
                logger.info("Logging in")
                await self.login(client)
            else:
                logger.info("Missing credentials: skipping login.")

            # Fetch first page
            logger.info("Fetching first product page to determine total count…")

            first_html = await self.fetch(client, self.config.urls.products_url)

            total_products = ProductHTMLParser().extract_total_products(first_html.text)
            got_pages = math.ceil(
                total_products / int(self.config.urls.list_limit_value)
            )
            total_pages: int = (
                min(got_pages, max_pages) if max_pages is not None else got_pages
            )
            logger.info(
                "Total products: %d → Total pages: %d (max pages: %s)",
                total_products,
                got_pages,
                max_pages,
            )

            # Skip saving the first page if requested
            if skip == 0:
                first_path = Path(output, "page_1.html")
                first_path.write_text(first_html.text, encoding="utf-8")

            # URLs for remaining pages
            urls: list[tuple[int, str]] = [
                (
                    page,
                    f"{self.config.urls.products_url}&p={page}",
                )
                for page in range(2 + skip, total_pages + 1)
            ]

            async def wrapped_fetch(page_num: int, url: str):
                html = await self.fetch(client, url)

                logger.info("Page %d fetched, saving to disk…", page_num)

                path = Path(output, f"page_{page_num}.html")
                path.write_text(html.text, encoding="utf-8")

                return path

            # Parallel download
            await asyncio.gather(*[wrapped_fetch(page, url) for page, url in urls])

            logger.info("All %d pages saved to '%s'", total_pages, output)

        return Path(output)

    async def request_prices(
        self,
        client: httpx.AsyncClient,
        pids: list[int] | None = None,
        products: list[Product] | None = None,
    ) -> dict:
        if pids is None and products is None:
            raise ValueError("Please provide either `pids` or `products`.")

        pids: list[int] = pids or [p.product_id for p in products]

        headers = self.config.user_agents.get_random_ua_header()
        headers.update({"Accept": "application/json"})

        await self.login(client)

        response = await client.get(
            self.config.urls.prices_url,
            headers=headers,
            params={"pids": pids},
            follow_redirects=True,
        )
        response.raise_for_status()

        return response.json()
