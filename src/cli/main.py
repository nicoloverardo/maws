import asyncio
import datetime
import logging
from pathlib import Path
from typing import Annotated, Optional
from uuid import uuid4

import typer
from rich.logging import RichHandler

from maws import MawsAsyncClient
from maws.playwright import main

app = typer.Typer(no_args_is_help=True)

logging_format = "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
logging.basicConfig(
    level=logging.DEBUG,
    format=logging_format,
    handlers=[
        RichHandler(level=logging.INFO),
        logging.FileHandler("maws.log", encoding="utf-8"),
    ],
)


@app.callback()
def callback():
    """
    Magento Asia Website Scraper
    """


products_app = typer.Typer(no_args_is_help=True)


@products_app.command()
def download_list(
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
def download_details(
    products: Annotated[
        Path,
        typer.Option(
            help="Path to the JSON file containing product data.",
            file_okay=True,
            dir_okay=False,
            readable=True,
            exists=True,
        ),
    ],
    output: Annotated[
        Optional[Path],
        typer.Option(
            help="Where to save the downloaded pages",
            file_okay=False,
            dir_okay=True,
            writable=True,
        ),
    ] = None,
    timeout: Annotated[
        int,
        typer.Option(
            help="Timeout for loading each product page, in milliseconds.",
            min=1,
        ),
    ] = 30000,
):
    """Download Products details page."""
    if output is None:
        output = Path("output", str(uuid4()))
    output.mkdir(parents=True, exist_ok=True)
    asyncio.run(main(products=products, output=output, timeout=timeout))


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
    is_details: Annotated[
        bool,
        typer.Option(
            "--is-details",
            help="Whether the pages contain detailed product information.",
            is_flag=True,
        ),
    ] = False,
    input_json: Annotated[
        Optional[Path],
        typer.Option(
            help="Path to the input JSON file containing product data. Only used when --is-details is passed.",
            file_okay=True,
            dir_okay=False,
            readable=True,
            exists=True,
        ),
    ] = None,
):
    """Parse a folder containing HTML downloaded pages and save them to JSON."""
    client = MawsAsyncClient()
    name_part = "products_detailed" if is_details else "products"
    file_name = (
        datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + name_part + ".json"
    )
    if is_details:
        _ = client.parse_detailed_product_folder(
            folder=source, input_json=input_json, output_json=Path(output, file_name)
        )
    else:
        _ = client.parse_folder(folder=source, output_json=Path(output, file_name))


app.add_typer(products_app, name="products", help="Commands related to Products.")
