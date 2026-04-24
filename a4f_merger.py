"""
a4f_merger.py
-----------------------
Merges scraped product data with original product list JSON.



Usage — CLI
-----------
    uv run a4f_merger.py --source-json products.json --scraped-dir out/ --output-file merged.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

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
# Merge helper
# ---------------------------------------------------------------------------


def merge(
    source_json: str | Path,
    scraped_dir: str | Path,
    output_file: str | Path,
) -> list[dict[str, Any]]:
    """
    Merge the original product list JSON with per-product scraped attribute
    files, writing a single enriched JSON to *output_file*.

    Merge logic
    -----------
    A scraped file is joined into its source record when **both** conditions
    hold:

    1. The source record has a non-null ``product_url``.
    2. The scraped file contains a non-null ``url`` **and** a non-null,
       non-empty ``attributes`` dict.

    The scraped fields ``product_id``, ``attributes``, and ``variant_data``
    are merged into the source record under an ``"enriched"`` key so the
    original structure is never mutated.  Records that do not match any
    scraped file are included as-is (without an ``"enriched"`` key).

    Parameters
    ----------
    source_json:
        Path to the original Pydantic-model-dump JSON (list of product dicts
        each containing a ``"product_url"`` key).
    scraped_dir:
        Directory that was passed as ``--output`` during scraping; every
        ``*.json`` file inside is read and indexed by its ``url`` field.
    output_file:
        Destination path for the merged JSON file.  Parent directories are
        created if absent.

    Returns
    -------
    The merged list of dicts (also written to *output_file*).

    Examples
    --------
    .. code-block:: python

        from asia4friends_product import merge

        merged = merge(
            source_json="products.json",
            scraped_dir="out/",
            output_file="merged.json",
        )
        print(f"Merged {len(merged)} records")
    """
    source_path = Path(source_json)
    scraped_path = Path(scraped_dir)
    output_path = Path(output_file)

    # ---- Load source records -----------------------------------------------
    source_records: list[dict[str, Any]] = json.loads(
        source_path.read_text(encoding="utf-8")
    )

    # ---- Index scraped files by their url field ----------------------------
    # Only keep entries that have both a url and non-empty attributes.
    scraped_index: dict[str, dict[str, Any]] = {}
    skipped = 0
    for json_file in sorted(scraped_path.glob("*.json")):
        try:
            data: dict[str, Any] = json.loads(json_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            console.print(f"[yellow]⚠ could not read {json_file.name}: {exc}[/yellow]")
            continue

        url = data.get("url")
        attributes = data.get("attributes")

        if not url or not attributes:
            skipped += 1
            continue

        scraped_index[url] = data

    console.print(
        f"[dim]Indexed [bold]{len(scraped_index)}[/bold] scraped files "
        f"({skipped} skipped — null url or empty attributes)[/dim]"
    )

    # ---- Merge -------------------------------------------------------------
    merged: list[dict[str, Any]] = []
    matched = 0
    unmatched = 0

    for record in source_records:
        product_url: str | None = record.get("product_url")

        if product_url and product_url in scraped_index:
            scraped = scraped_index[product_url]
            enriched_record = {
                **record,
                "enriched": {
                    "product_id": scraped.get("product_id"),
                    "attributes": scraped.get("attributes"),
                    "variant_data": scraped.get("variant_data"),
                },
            }
            merged.append(enriched_record)
            matched += 1
        else:
            merged.append(record)
            unmatched += 1

    # ---- Write output ------------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # ---- Summary -----------------------------------------------------------
    table = Table(title="Merge Summary", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="dim")
    table.add_column("Value", justify="right")
    table.add_row("Source records", str(len(source_records)))
    table.add_row("Scraped files indexed", str(len(scraped_index)))
    table.add_row("[green]Matched & enriched[/green]", str(matched))
    table.add_row("[yellow]Unmatched (kept as-is)[/yellow]", str(unmatched))
    table.add_row("Output", str(output_path.resolve()))
    console.print(table)

    return merged


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


@app.command(name="merge")
def merge_cmd(
    source_json: Annotated[
        Path,
        typer.Option(
            help="Path to the original products JSON (list of Pydantic model dicts)."
        ),
    ],
    scraped_dir: Annotated[
        Path,
        typer.Option(help="Directory containing the per-product scraped *.json files."),
    ],
    output_file: Annotated[
        Path,
        typer.Option(help="Destination path for the merged JSON output file."),
    ],
) -> None:
    """
    Merge the original product list with scraped attribute files.

    Joins on product_url (source) <-> url (scraped), only when both are
    non-null and the scraped file contains non-empty attributes.
    """
    merge(source_json=source_json, scraped_dir=scraped_dir, output_file=output_file)


if __name__ == "__main__":
    app()
