import logging

import typer
from rich.logging import RichHandler

from .a4f import a4f
from .aof import aof
from .goa import goa

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


app.add_typer(aof, name="aof", help="Commands related to Asia Express Food.")
app.add_typer(goa, name="goa", help="Commands related to Go Asia.")
app.add_typer(a4f, name="a4f", help="Commands related to Asia 4 Friends.")
