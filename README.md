# maws

Parser of the Asia Express website built on Magento.

[![CI Pipeline](https://github.com/nicoloverardo/maws/actions/workflows/ci.yaml/badge.svg)](https://github.com/nicoloverardo/maws/actions/workflows/ci.yaml)
![GitHub License](https://img.shields.io/github/license/nicoloverardo/maws)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Description

`maws` is an asynchronous scraper and parser for the Asia Express website (built on Magento). It can download product listing pages while respecting configurable rate limits and optional login credentials, parse the downloaded HTML into structured `Product` models, and query product prices via the site's API.

The library exposes a small async client (`MawsAsyncClient`) to perform the network operations and a parser to convert saved pages into JSON-ready Python objects.

## Usage

Typical usage (via the CLI) would be that:

1. You first retrieve the list of products via `maws products download-list`
2. You then parse the folder where the HTMLs have been downloaded via `maws products parse` to create a JSON with the products overview info (e.g. ID, name)
3. You then retrieve product details (e.g. price) for each product in the JSON via `maws products download-details`.
4. Finally, you parse the folder with the HTML of the product pages to a more comprehensive JSON via `maws products parse --is-details`.

## CLI

Magento Asia Website Scraper

**Usage**:

```console
$ maws [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `products`: Commands related to Products.

### `maws products`

Commands related to Products.

**Usage**:

```console
$ maws products [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `download-list`: Download pages.
* `download-details`: Download Products details page.
* `parse`: Parse a folder containing HTML downloaded...

#### `maws products download-list`

Download pages.

**Usage**:

```console
$ maws products download-list [OPTIONS]
```

**Options**:

* `--output DIRECTORY`: Where to save the downloaded pages  [required]
* `--max-pages INTEGER RANGE`: The maximum number of pages to download.  [x&gt;=1]
* `--skip INTEGER RANGE`: How many pages to skip.  [default: 0; x&gt;=0]
* `--help`: Show this message and exit.

#### `maws products download-details`

Download Products details page.

**Usage**:

```console
$ maws products download-details [OPTIONS]
```

**Options**:

* `--products FILE`: Path to the JSON file containing product data.  [required]
* `--output DIRECTORY`: Where to save the downloaded pages
* `--timeout INTEGER RANGE`: Timeout for loading each product page, in milliseconds.  [default: 30000; x&gt;=1]
* `--help`: Show this message and exit.

#### `maws products parse`

Parse a folder containing HTML downloaded pages and save them to JSON.

**Usage**:

```console
$ maws products parse [OPTIONS]
```

**Options**:

* `--source DIRECTORY`: Folder where the downloaded pages are saved.  [required]
* `--output DIRECTORY`: Folder where to save the JSON file.  [required]
* `--is-details`: Whether the pages contain detailed product information.
* `--input-json FILE`: Path to the input JSON file containing product data. Only used when --is-details is passed.
* `--help`: Show this message and exit.

## Python usage

Below are simple examples showing common usages of `MawsAsyncClient`.

Download product pages (uses the same client the CLI uses):

```python
from pathlib import Path
import asyncio
from maws import MawsAsyncClient

client = MawsAsyncClient()
asyncio.run(client.download_all_products(output=Path("output"), max_pages=10, skip=0))
```

Parse previously downloaded pages into `Product` objects and save to JSON:

```python
from pathlib import Path
from maws import MawsAsyncClient

client = MawsAsyncClient()
products = client.parse_folder(Path("output"), output_json=Path("output/products.json"))
print(f"Parsed {len(products)} products")
```

See the CLI in `src/cli/main.py` for how the client is used in practice.
