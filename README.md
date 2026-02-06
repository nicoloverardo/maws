# maws

Parser of the Asia Express website built on Magento.

[![CI Pipeline](https://github.com/nicoloverardo/maws/actions/workflows/ci.yaml/badge.svg)](https://github.com/nicoloverardo/maws/actions/workflows/ci.yaml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Description

TODO

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

* `download`: Download pages.
* `parse`: Parse a folder containing HTML downloaded...

#### `maws products download`

Download pages.

**Usage**:

```console
$ maws products download [OPTIONS]
```

**Options**:

* `--output DIRECTORY`: Where to save the downloaded pages  [required]
* `--max-pages INTEGER RANGE`: The maximum number of pages to download.  [x&gt;=1]
* `--skip INTEGER RANGE`: How many pages to skip.  [default: 0; x&gt;=0]
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
* `--help`: Show this message and exit.

## Python usage

TODO
