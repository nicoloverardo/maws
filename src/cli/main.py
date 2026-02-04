import typer


app = typer.Typer()


@app.callback()
def callback():
    """
    Magento Asia Website Scraper
    """


@app.command()
def hello():
    """
    Say hello to the user
    """
    typer.echo("Hello from Magento Asia Website Scraper!")
