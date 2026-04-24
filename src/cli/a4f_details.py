"""
asia4friends_product.py
-----------------------
Scrapes product attribute/details tables from asia4friends.de (JTL-Shop 5.x).

Supports two modes:
  • Single product  — pass a slug or full URL directly.
  • Batch           — pass a path to a JSON file containing a list of product
                      dicts (as exported from the Pydantic model).  All URLs
                      are fetched in parallel with a configurable concurrency
                      limit and Rich progress reporting.

Dependencies
------------
    pip install httpx beautifulsoup4 lxml typer rich

Usage — library
---------------
    import asyncio
    from asia4friends_product import run

    # Single product
    asyncio.run(run(product="frische-vietnamesische-melisse-aus-asien-100g"))

    # Batch from file
    asyncio.run(run(product="products.json", output="out/"))

Usage — CLI
-----------
    # Single product, print to stdout
    uv run a4f_details.py frische-vietnamesische-melisse-aus-asien-100g

    # Batch from JSON file, save each result to ./out/
    uv run a4f_details.py products.json --output out/

    # With optional flags
    uv run a4f_details.py products.json --output out/ --variants --concurrency 10
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlparse

import httpx
import typer
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://asia4friends.de"

_PAGE_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}

_IO_HEADERS: dict[str, str] = {
    **_PAGE_HEADERS,
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
}

console = Console(stderr=True)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ProductDetails:
    """Successful scrape result for a single product."""

    url: str
    product_id: int | None
    name: str | None
    attributes: dict[str, dict[str, str]] = field(default_factory=dict)
    variant_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "product_id": self.product_id,
            "name": self.name,
            "attributes": self.attributes,
            "variant_data": self.variant_data,
        }


@dataclass
class FetchError:
    """Represents a failed fetch attempt."""

    url: str
    error: str

    def to_dict(self) -> dict[str, Any]:
        return {"url": self.url, "error": self.error}


# ---------------------------------------------------------------------------
# Scraper class
# ---------------------------------------------------------------------------


class Asia4FriendsScraper:
    """
    Async scraper for product detail pages on asia4friends.de (JTL-Shop 5.x).

    Reuses a single :class:`httpx.AsyncClient` across all calls — use it as
    an async context manager so the connection pool is cleaned up properly:

    .. code-block:: python

        async with Asia4FriendsScraper() as scraper:
            details = await scraper.fetch(
                "frische-vietnamesische-melisse-aus-asien-100g"
            )
    """

    def __init__(self, *, timeout: float = 15.0) -> None:
        self._timeout = timeout
        self._client = httpx.AsyncClient(
            headers=_PAGE_HEADERS,
            timeout=timeout,
            follow_redirects=True,
        )

    async def __aenter__(self) -> "Asia4FriendsScraper":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fetch(
        self,
        slug_or_url: str,
        *,
        include_variant_data: bool = False,
    ) -> ProductDetails:
        """
        Fetch and parse a single product page.

        Raises :class:`httpx.HTTPStatusError` on 4xx/5xx.
        """
        url = self._normalise_url(slug_or_url)
        response = await self._client.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        variant_data: dict[str, Any] = {}
        product_id = self._extract_product_id(soup)
        if include_variant_data and product_id is not None:
            variant_data = await self._fetch_variant_data(product_id)

        return ProductDetails(
            url=url,
            product_id=product_id,
            name=self._extract_name(soup),
            attributes=self._parse_attribute_tables(soup),
            variant_data=variant_data,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_url(slug_or_url: str) -> str:
        slug_or_url = slug_or_url.strip()
        if slug_or_url.startswith("http"):
            return slug_or_url
        return f"{BASE_URL}/{slug_or_url.lstrip('/')}"

    @staticmethod
    def _extract_name(soup: BeautifulSoup) -> str | None:
        h1 = soup.find("h1")
        return h1.get_text(strip=True) if h1 else None

    @staticmethod
    def _extract_product_id(soup: BeautifulSoup) -> int | None:
        """
        Tries three locations in order of reliability:
        1. ``<input type="hidden" name="kArtikel" value="…">``
        2. Breadcrumb anchor  ``…#buy_form_1185``
        3. Inline ``<script>`` variable  ``kArtikel = 1185``
        """
        tag = soup.find("input", {"name": "kArtikel"})
        if tag and str(tag.get("value", "")).isdigit():
            return int(tag["value"])  # ty:ignore[invalid-argument-type]

        for a in soup.find_all("a", href=True):
            m = re.search(r"#buy_form_(\d+)", a["href"])  # ty:ignore[no-matching-overload]
            if m:
                return int(m.group(1))

        for script in soup.find_all("script"):
            m = re.search(r"\bkArtikel\s*[=:]\s*(\d+)", script.string or "")
            if m:
                return int(m.group(1))

        return None

    @staticmethod
    def _parse_attribute_tables(soup: BeautifulSoup) -> dict[str, dict[str, str]]:
        """
        Collects every ``<table>`` on the page into
        ``{ section_heading: { label: value } }``.
        """
        results: dict[str, dict[str, str]] = {}

        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            if not rows:
                continue

            caption = table.find("caption")
            if caption:
                heading = caption.get_text(strip=True)
            else:
                heading = "Produkteigenschaften"
                for sib in table.find_previous_siblings():
                    text = sib.get_text(strip=True)
                    if text:
                        heading = text
                        break

            attrs: dict[str, str] = {}
            for row in rows:
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:  # noqa: PLR2004
                    key = cells[0].get_text(strip=True).rstrip(":")
                    value = cells[1].get_text(strip=True)
                    if key:
                        attrs[key] = value

            if attrs:
                results.setdefault(heading, {}).update(attrs)

        return results

    async def _fetch_variant_data(self, product_id: int) -> dict[str, Any]:
        """POST to JTL-Shop's internal ``/io`` to get variant child-article JSON."""
        try:
            response = await self._client.post(
                f"{BASE_URL}/io",
                data={"action": "getArticleById", "kArtikel": str(product_id)},
                headers=_IO_HEADERS,
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError):
            return {}


# ---------------------------------------------------------------------------
# Helpers — I/O
# ---------------------------------------------------------------------------


def _slug_from_url(url: str) -> str:
    """Return a filesystem-safe filename stem derived from a product URL."""
    path = urlparse(url).path.strip("/")
    # Keep only the last segment (the slug itself)
    slug = path.split("/")[-1] if "/" in path else path
    # Sanitise any remaining odd characters
    return re.sub(r"[^\w\-]", "_", slug)


def _load_urls_from_json(json_path: Path) -> list[str]:
    """
    Load a list of product dicts from *json_path* and return their
    ``product_url`` values.  Dicts that lack the key are skipped with a
    warning.
    """
    raw: list[dict[str, Any]] = json.loads(json_path.read_text(encoding="utf-8"))
    urls: list[str] = []
    for item in raw:
        url = item.get("product_url")
        if url:
            urls.append(url)
        else:
            console.print(
                f"[yellow]⚠ skipping entry without 'product_url': "
                f"{item.get('name') or item}[/yellow]"
            )
    return urls


def _write_result(
    result: ProductDetails | FetchError,
    output_dir: Path,
) -> Path:
    """Serialise *result* to ``<output_dir>/<slug>.json`` and return the path."""
    slug = _slug_from_url(result.url)
    dest = output_dir / f"{slug}.json"
    dest.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return dest


# ---------------------------------------------------------------------------
# Core batch runner
# ---------------------------------------------------------------------------


async def _fetch_one(  # noqa: PLR0913
    scraper: Asia4FriendsScraper,
    url: str,
    *,
    include_variant_data: bool,
    progress: Progress,
    task_id: Any,
    output_dir: Path | None,
) -> ProductDetails | FetchError:
    """Fetch a single URL, update progress, optionally write output."""
    result: ProductDetails | FetchError
    try:
        result = await scraper.fetch(url, include_variant_data=include_variant_data)
        progress.advance(task_id)
        progress.update(task_id, description=f"[green]✓[/green] {url}")
    except Exception as exc:  # noqa: BLE001
        result = FetchError(url=url, error=str(exc))
        progress.advance(task_id)
        progress.update(task_id, description=f"[red]✗[/red] {url}")
        console.print(f"[red]  ERROR[/red] {url}\n         {exc}")

    if output_dir is not None:
        _write_result(result, output_dir)

    return result


async def _run_batch(
    urls: list[str],
    *,
    include_variant_data: bool,
    concurrency: int,
    timeout: float,
    output_dir: Path | None,
) -> list[ProductDetails | FetchError]:
    """Fetch all *urls* in parallel up to *concurrency* at a time."""
    semaphore = asyncio.Semaphore(concurrency)
    results: list[ProductDetails | FetchError] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    ) as progress:
        task_id = progress.add_task(
            f"Fetching [bold]{len(urls)}[/bold] products…",
            total=len(urls),
        )

        async with Asia4FriendsScraper(timeout=timeout) as scraper:

            async def _bounded(url: str) -> ProductDetails | FetchError:
                async with semaphore:
                    return await _fetch_one(
                        scraper,
                        url,
                        include_variant_data=include_variant_data,
                        progress=progress,
                        task_id=task_id,
                        output_dir=output_dir,
                    )

            results = list(await asyncio.gather(*[_bounded(u) for u in urls]))

    return results


# ---------------------------------------------------------------------------
# Public run() — single entry point for library & CLI
# ---------------------------------------------------------------------------


async def run(
    product: str,
    *,
    include_variant_data: bool = False,
    concurrency: int = 5,
    timeout: float = 15.0,
    output: str | Path | None = None,
) -> list[ProductDetails | FetchError]:
    """
    Fetch product details and print / save results.

    Parameters
    ----------
    product:
        One of:
        - A product slug, e.g. ``"frische-vietnamesische-melisse-aus-asien-100g"``
        - A full product URL
        - A path to a JSON file containing a list of product dicts, each
          having a ``"product_url"`` key (Pydantic model dump format).
    include_variant_data:
        Also POST to ``/io`` for raw variant JSON.
    concurrency:
        Maximum number of parallel requests (batch mode only).
    timeout:
        HTTP timeout per request in seconds.
    output:
        Directory path.  When set, each result is written as
        ``<output>/<slug>.json``.  The directory is created if absent.

    Returns
    -------
    List of :class:`ProductDetails` or :class:`FetchError` objects.

    Examples
    --------
    .. code-block:: python

        import asyncio
        from asia4friends_product import run

        # Single product
        asyncio.run(run(product="frische-vietnamesische-melisse-aus-asien-100g"))

        # Batch
        asyncio.run(run(product="products.json", output="out/", concurrency=8))
    """
    output_dir: Path | None = None
    if output is not None:
        output_dir = Path(output)
        output_dir.mkdir(parents=True, exist_ok=True)

    # ---- Determine mode: JSON file path vs. single slug/URL ----------------
    product_path = Path(product)
    if product_path.suffix.lower() == ".json" and product_path.exists():
        urls = _load_urls_from_json(product_path)
        if not urls:
            console.print("[yellow]No product URLs found in the JSON file.[/yellow]")
            return []
        console.print(
            f"[bold cyan]Batch mode:[/bold cyan] {len(urls)} products "
            f"from [italic]{product_path}[/italic]"
        )
        results = await _run_batch(
            urls,
            include_variant_data=include_variant_data,
            concurrency=concurrency,
            timeout=timeout,
            output_dir=output_dir,
        )
    else:
        # Single product — still route through _run_batch for consistent
        # error handling and output writing.
        console.print(f"[bold cyan]Single mode:[/bold cyan] {product}")
        results = await _run_batch(
            [product],
            include_variant_data=include_variant_data,
            concurrency=1,
            timeout=timeout,
            output_dir=output_dir,
        )

    # ---- Summary -----------------------------------------------------------
    successes = [r for r in results if isinstance(r, ProductDetails)]
    errors = [r for r in results if isinstance(r, FetchError)]

    _print_summary(
        results=results, successes=successes, errors=errors, output_dir=output_dir
    )

    # ---- If single product and no output dir, print JSON to stdout ---------
    if len(results) == 1 and output_dir is None and successes:
        print(json.dumps(successes[0].to_dict(), ensure_ascii=False, indent=2))

    return results


def _print_summary(
    results: list[ProductDetails | FetchError],
    successes: list[ProductDetails],
    errors: list[FetchError],
    output_dir: Path | None,
) -> None:
    table = Table(title="Scrape Summary", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="dim")
    table.add_column("Value", justify="right")
    table.add_row("Total", str(len(results)))
    table.add_row("[green]Succeeded[/green]", str(len(successes)))
    table.add_row("[red]Failed[/red]", str(len(errors)))
    if output_dir:
        table.add_row("Output dir", str(output_dir.resolve()))
    console.print(table)

    if errors:
        console.print("\n[bold red]Failed URLs:[/bold red]")
        for e in errors:
            console.print(f"  [red]•[/red] {e.url}\n    [dim]{e.error}[/dim]")


# ---------------------------------------------------------------------------
# Typer CLI
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="asia4friends",
    help=(
        "Scrape product attribute tables from asia4friends.de (JTL-Shop).\n\n"
        "PRODUCT can be a slug, a full URL, or a path to a JSON file."
    ),
    add_completion=False,
)


@app.command()
def main(
    product: str = typer.Argument(
        ...,
        help=(
            "Product slug, full URL, or path to a JSON file containing "
            "a list of product dicts with a 'product_url' key."
        ),
    ),
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Directory to write one JSON file per product. Created if absent.",
            file_okay=False,
            resolve_path=True,
        ),
    ] = None,
    variants: Annotated[
        bool,
        typer.Option(
            "--variants",
            "-v",
            help="Also fetch variant child-article data from /io.",
        ),
    ] = False,
    concurrency: Annotated[
        int,
        typer.Option(
            "--concurrency",
            "-c",
            help="Maximum number of parallel requests (batch mode).",
            min=1,
            max=50,
        ),
    ] = 5,
    timeout: Annotated[
        float,
        typer.Option(
            "--timeout",
            "-t",
            help="HTTP request timeout in seconds.",
        ),
    ] = 15.0,
) -> None:
    """Fetch and print/save product attributes as JSON."""
    asyncio.run(
        run(
            product=product,
            include_variant_data=variants,
            concurrency=concurrency,
            timeout=timeout,
            output=output,
        )
    )


if __name__ == "__main__":
    app()
