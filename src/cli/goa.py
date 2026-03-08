import asyncio
from pathlib import Path
from typing import Annotated

import typer

from maws import GoaAsyncClient

goa = typer.Typer(no_args_is_help=True)


@goa.command()
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
    timeout: Annotated[
        int,
        typer.Option(help="The maximum time to spend downloading pages.", min=1000),
    ] = 60000,
    headless: Annotated[
        bool,
        typer.Option(help="Whether to run the browser in headless mode."),
    ] = True,
):
    """Download pages."""
    client = GoaAsyncClient()
    asyncio.run(
        client.parse_all_with_playwright(
            output=output, headless=headless, timeout=timeout
        )
    )
