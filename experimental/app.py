"""Async typer app with rich progress to download all assortiment pages."""

import asyncio
import math
import os
import re
from pathlib import Path

import httpx
import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)

app = typer.Typer()
console = Console()

BASE_URL = "https://order.asiaexpressfood.nl/en/assortiment.html"
PRODUCTS_PER_PAGE = 48
RATE_LIMIT_SECONDS = 1.0
OUTPUT_DIR = "output"


def extract_total_products(html: str) -> int:
    """
    Extracts total product count from header like:
    'Products (4498)'
    """
    match = re.search(r"Products\s*\((\d+)\)", html)
    if not match:
        raise RuntimeError("Could not find total product count in page")
    return int(match.group(1))


async def fetch(
    client: httpx.AsyncClient,
    url: str,
    rate_limiter: asyncio.Semaphore,
) -> str:
    async with rate_limiter:
        response = await client.get(url)
        response.raise_for_status()
        await asyncio.sleep(RATE_LIMIT_SECONDS)
        return response.text


async def download_all_pages():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    rate_limiter = asyncio.Semaphore(1)

    async with httpx.AsyncClient(timeout=30) as client:
        # Fetch first page
        first_url = f"{BASE_URL}?product_list_limit={PRODUCTS_PER_PAGE}"
        console.print("[bold]Fetching first page to determine total count…[/bold]")
        first_html = await fetch(client, first_url, rate_limiter)

        total_products = extract_total_products(first_html)
        total_pages = math.ceil(total_products / PRODUCTS_PER_PAGE)
        console.print(
            f"[green]Total products:[/green] {total_products} → "
            f"[green]Total pages:[/green] {total_pages}"
        )

        # Save first page
        first_path = Path(OUTPUT_DIR, "page_1.html")
        first_path.write_text(first_html, encoding="utf-8")

        # URLs for remaining pages
        urls = [
            (page, f"{BASE_URL}?p={page}&product_list_limit={PRODUCTS_PER_PAGE}")
            for page in range(2, total_pages + 1)
        ]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                "Downloading pages…",
                total=len(urls),
            )

            async def wrapped_fetch(page_num: int, url: str):
                html = await fetch(client, url, rate_limiter)
                # Save page to disk
                path = Path(OUTPUT_DIR, f"page_{page_num}.html")
                path.write_text(html, encoding="utf-8")

                progress.advance(task)
                return path

            # Parallel download
            await asyncio.gather(*[wrapped_fetch(page, url) for page, url in urls])

        console.print(
            f"[bold green]All {total_pages} pages saved to '{OUTPUT_DIR}'[/bold green]"
        )


@app.command()
def download():
    """
    Download all assortiment pages and save them to disk in 'output/' folder.
    """
    asyncio.run(download_all_pages())


if __name__ == "__main__":
    app()
