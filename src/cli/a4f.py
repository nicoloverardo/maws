import asyncio
from pathlib import Path
from typing import Annotated

import typer

from maws.a4f.client import main

a4f = typer.Typer(no_args_is_help=True)


@a4f.command()
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
):
    """Download pages."""
    asyncio.run(main(folder_path=output))
