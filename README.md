# maws

Parser of the Asia Express website built on Magento and Asia 4 Friends.

[![CI Pipeline](https://github.com/nicoloverardo/maws/actions/workflows/ci.yaml/badge.svg)](https://github.com/nicoloverardo/maws/actions/workflows/ci.yaml)
![GitHub License](https://img.shields.io/github/license/nicoloverardo/maws)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Description

`maws` is an asynchronous scraper and parser for the Asia Express website (built on Magento). It can download product listing pages while respecting configurable rate limits and optional login credentials, parse the downloaded HTML into structured `Product` models, and query product prices via the site's API.

The library exposes a small async client (`MawsAsyncClient`) to perform the network operations and a parser to convert saved pages into JSON-ready Python objects.

Moreover, it can also parse the GoAsia website.

## Requirements

- Python 3.10+
- git

You can get Python via `uv`. Follow the [official uv guide](https://docs.astral.sh/uv/getting-started/installation/) to install `uv`.

## Setup

1. Clone the repository.
2. Once you have `uv` installed, you simply need to run `uv sync --all-groups --all-extras` to install Python, create a virtual env, and download all the Python dependencies.
3. Install the required dependencies for playwright: `uv run playwright install chromium chromium-headless-shell --with-deps`.

## Usage

### Asia Express

Typical usage (via the CLI) would be that:

1. Set in a `.env` file the `MAWS_USERNAME` and `MAWS_PASSWORD` variables to your credentials.
2. Open a terminal and source the `.env` file: `set -o allexport && source .env && set +o allexport`.
3. In the same terminal, you first retrieve the list of products via `maws products download-list` (or preprend `uv run` to all commands if running via `uv`).
4. You then parse the folder where the HTMLs have been downloaded via `maws products parse` to create a JSON with the products overview info (e.g. ID, name)
5. You then retrieve product details (e.g. price) for each product in the JSON via `maws products download-details`.
6. Finally, you parse the folder with the HTML of the product pages to a more comprehensive JSON via `maws products parse --is-details`.

### Asia 4 Friends

1. First download all products via the CLI using `uv run maws a4f download --output out_folder`. Will create a `products.json` in the output folder.
2. Then download all the details with `uv run src/cli/a4f_details.py output/products.json --output output/details --concurrency 10`.
3. Finally, merge all data into a single JSON with `uv run src/cli/a4f_merger.py --source-json output/products.json --scraped-dir output/details/ --output-file asia4friends_with_details.json`
