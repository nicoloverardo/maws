import asyncio
import datetime
import logging
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.logging import RichHandler

from maws import MawsAsyncClient

app = typer.Typer(no_args_is_help=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    handlers=[RichHandler()],
)


@app.callback()
def callback():
    """
    Magento Asia Website Scraper
    """


products_app = typer.Typer(no_args_is_help=True)


@products_app.command()
def download(
    output: Annotated[
        Path,
        typer.Option(
            help="Where to save the downloaded pages",
            file_okay=False,
            dir_okay=True,
            writable=True,
        ),
    ],
    max_pages: Annotated[
        Optional[int],
        typer.Option(help="The maximum number of pages to download.", min=1),
    ] = None,
    skip: Annotated[
        int,
        typer.Option(help="How many pages to skip.", min=0),
    ] = 0,
):
    """Download pages."""
    client = MawsAsyncClient()
    asyncio.run(
        client.download_all_products(output=output, max_pages=max_pages, skip=skip)
    )


@products_app.command()
def parse(
    source: Annotated[
        Path,
        typer.Option(
            help="Folder where the downloaded pages are saved.",
            file_okay=False,
            dir_okay=True,
            readable=True,
            exists=True,
        ),
    ],
    output: Annotated[
        Path,
        typer.Option(
            help="Folder where to save the JSON file.",
            file_okay=False,
            dir_okay=True,
            writable=True,
        ),
    ],
):
    """Parse a folder containing HTML downloaded pages and save them to JSON."""
    client = MawsAsyncClient()
    file_name = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + "_products.json"
    _ = client.parse_folder(folder=source, output_json=Path(output, file_name))


app.add_typer(products_app, name="products", help="Commands related to Products.")
