# CLI

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

* `aof`: Commands related to Asia Express Food.

## `maws aof`

Commands related to Asia Express Food.

**Usage**:

```console
$ maws aof [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `products`: Commands related to Products.

### `maws aof products`

Commands related to Products.

**Usage**:

```console
$ maws aof products [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `download-list`: Download pages.
* `download-details`: Download Products details page.
* `parse`: Parse a folder containing HTML downloaded...

#### `maws aof products download-list`

Download pages.

**Usage**:

```console
$ maws aof products download-list [OPTIONS]
```

**Options**:

* `--output DIRECTORY`: Where to save the downloaded pages  [required]
* `--max-pages INTEGER RANGE`: The maximum number of pages to download.  [x&gt;=1]
* `--skip INTEGER RANGE`: How many pages to skip.  [default: 0; x&gt;=0]
* `--help`: Show this message and exit.

#### `maws aof products download-details`

Download Products details page.

**Usage**:

```console
$ maws aof products download-details [OPTIONS]
```

**Options**:

* `--products FILE`: Path to the JSON file containing product data.  [required]
* `--output DIRECTORY`: Where to save the downloaded pages
* `--timeout INTEGER RANGE`: Timeout for loading each product page, in milliseconds.  [default: 30000; x&gt;=1]
* `--help`: Show this message and exit.

#### `maws aof products parse`

Parse a folder containing HTML downloaded pages and save them to JSON.

**Usage**:

```console
$ maws aof products parse [OPTIONS]
```

**Options**:

* `--source DIRECTORY`: Folder where the downloaded pages are saved.  [required]
* `--output DIRECTORY`: Folder where to save the JSON file.  [required]
* `--is-details`: Whether the pages contain detailed product information.
* `--input-json FILE`: Path to the input JSON file containing product data. Only used when --is-details is passed.
* `--help`: Show this message and exit.
