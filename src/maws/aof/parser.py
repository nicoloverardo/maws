import re
from html.parser import HTMLParser


class ProductHTMLParser(HTMLParser):
    """Extracts the HTML items from the list of products.

    Examples:
        >>> parser = ProductHTMLParser()
        >>> parser.feed(html)
        >>> products = [Product(**p) for p in parser.products]
        >>> for product in products:
        ...     print(product.model_dump())
    """

    def __init__(self):
        super().__init__()

        self.products: list[dict] = []

        self.in_target_ol = False
        self.ol_depth = 0

        self.in_product_div = False
        self.product_div_depth = 0
        self.current_product: dict = {}

        self.capture_field: str | None = None
        self.text_buffer: list[str] = []

    def handle_starttag(self, tag, attrs):  # noqa: PLR0912
        attrs = dict(attrs)

        # Find ol anywhere
        if tag == "ol" and attrs.get("class") == "products list items product-items":
            self.in_target_ol = True
            self.ol_depth = 1
            return

        if self.in_target_ol and tag == "ol":
            self.ol_depth += 1

        # Start product container
        if (
            self.in_target_ol
            and tag == "div"
            and attrs.get("class") == "product-item-info"
        ):
            self.in_product_div = True
            self.product_div_depth = 1
            product_id = attrs.get("data-product-id")
            self.current_product = {
                "product_id": int(product_id) if product_id else 0,
                # always present, even if missing in HTML
                "price": None,
                "tier_price": None,
                "best_before": None,
                "stock_status": None,
            }
            return

        if self.in_product_div and tag == "div":
            self.product_div_depth += 1

        if not self.in_product_div:
            return

        # URLs
        if tag == "a" and "product-item-photo" in attrs.get("class", ""):
            self.current_product["product_url"] = attrs.get("href")

        if tag == "img" and "product-image-photo" in attrs.get("class", ""):
            self.current_product["image_url"] = attrs.get("src")

        # Text fields
        if tag == "a" and attrs.get("class") == "product-item-link":
            self.capture_field = "name"

        elif tag == "div" and attrs.get("class") == "product-item-brand":
            self.capture_field = "brand"

        elif tag == "span" and attrs.get("itemprop") == "sku":
            self.capture_field = "sku"

        elif tag == "div" and attrs.get("class") == "product-item-unit":
            self.capture_field = "contents"

        # Price
        elif tag == "span" and attrs.get("class") == "price initialized-price":
            self.capture_field = "price"

        # Tier / bulk price
        elif tag == "span" and attrs.get("class") == "next-tier initialized-price":
            self.capture_field = "tier_price"

        # Best before
        elif tag == "span" and attrs.get("class") == "best_before":
            self.capture_field = "best_before"

        # Stock status
        elif tag == "div" and attrs.get("class", "").startswith("stock"):
            self.capture_field = "stock_status"

    def handle_data(self, data):
        if self.capture_field:
            stripped = data.strip()
            if stripped:
                self.text_buffer.append(stripped)

    def handle_endtag(self, tag):
        if self.capture_field:
            value = " ".join(self.text_buffer).strip()
            if value:
                self.current_product[self.capture_field] = value
            self.text_buffer.clear()
            self.capture_field = None

        if self.in_product_div and tag == "div":
            self.product_div_depth -= 1
            if self.product_div_depth == 0:
                self.products.append(self.current_product)
                self.current_product = {}
                self.in_product_div = False

        if self.in_target_ol and tag == "ol":
            self.ol_depth -= 1
            if self.ol_depth == 0:
                self.in_target_ol = False

    def extract_total_products(self, html: str) -> int:
        """Extracts total product count from header like: 'Products (4498)'."""
        match = re.search(r"Products\s*\((\d+)\)", html)
        if not match:
            return 4343  # Fallback to known count if not found
        return int(match.group(1))


class DetailedProductParser(HTMLParser):
    """Parses detailed product information from a product detail page HTML.

    Extracts:
    - Breadcrumb categories (excluding Home and Products)
    - Product description
    - Stock availability status
    - Price tier information
    - Product specifications table

    Examples:
        >>> parser = DetailedProductParser()
        >>> parser.feed(html)
        >>> product_data = parser.get_product_data()
    """

    MIN_TIER_PRICE_CELLS = 3
    TIER_QUANTITY_INDEX = 3
    TIER_PRICE_PIECE_INDEX = 4
    TIER_PRICE_BOX_INDEX = 5

    def __init__(self):
        """Initialize parser state."""
        super().__init__()

        self.categories: list[str] = []
        self.description: str | None = None
        self.stock_available: bool | None = None
        self.price_tiers: list[dict] = []
        self.specifications: dict = {}

        self.in_breadcrumbs = False
        self.breadcrumb_depth = 0
        self.capture_breadcrumb_name = False
        self.breadcrumb_buffer: list[str] = []

        self.in_description = False
        self.description_depth = 0
        self.description_buffer: list[str] = []

        self.in_stock_status = False
        self.stock_buffer: list[str] = []

        self.in_tier_price_table = False
        self.in_tier_price_row = False
        self.tier_cell_index = 0
        self.tier_quantity: str | None = None
        self.tier_price_piece: str | None = None
        self.tier_price_box: str | None = None
        self._tier_price_current_cell_skip = False

        self.in_specifications = False
        self.spec_depth = 0
        self.in_spec_dl = False
        self.current_spec_label: str | None = None
        self.spec_label_buffer: list[str] = []
        self.spec_value_buffer: list[str] = []

    def _start_breadcrumb(self, tag: str, attrs: dict) -> None:
        """Handle breadcrumb section start tags."""
        if tag == "div" and attrs.get("class") == "breadcrumbs":
            self.in_breadcrumbs = True
            self.breadcrumb_depth = 1
        elif tag == "span" and attrs.get("itemprop") == "name":
            self.capture_breadcrumb_name = True
        elif tag in ("ul", "li"):
            self.breadcrumb_depth += 1

    def _start_description(self, tag: str) -> None:
        """Handle description section start tags."""
        if tag == "div":
            if not self.in_description:
                self.in_description = True
                self.description_depth = 1
            else:
                self.description_depth += 1
        elif tag in ("ul", "li"):
            self.description_depth += 1

    def _start_tier_price(self, tag: str, attrs: dict) -> None:
        """Handle tier price section start tags."""
        if tag == "table" and attrs.get("id") == "tier-price-table":
            self.in_tier_price_table = True
        elif tag == "tr":
            self.in_tier_price_row = True
            self.tier_cell_index = 0
            self.tier_quantity = None
            self.tier_price_piece = None
            self.tier_price_box = None
        elif tag == "td" and self.in_tier_price_row:
            # Check if this TD should be skipped
            td_class = attrs.get("class", "")
            self.tier_cell_index += 1
            # Skip action, hidden and icon cells (indices 0, 1)
            # Only capture cells 2, 3, 4 (quantity, price_per_piece, price_per_box)
            self._tier_price_current_cell_skip = (
                "hidden" in td_class or "icon" in td_class or "action" in td_class
            )

    def _start_specifications(self, tag: str, attrs: dict) -> None:
        """Handle specifications section start tags."""
        if tag == "div":
            if "product-specifications-wrapper" in attrs.get("class", ""):
                self.in_specifications = True
                self.spec_depth = 1
            else:
                self.spec_depth += 1
        elif tag == "dl":
            self.in_spec_dl = True
        elif tag == "dt":
            self.spec_label_buffer = []
        elif tag == "dd":
            self.spec_value_buffer = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if self.in_breadcrumbs:
            self._start_breadcrumb(tag, attrs)
            return

        if tag == "div" and attrs.get("class") == "breadcrumbs":
            self._start_breadcrumb(tag, attrs)
            return

        if (
            self.in_description
            or tag == "div"
            and attrs.get("class") == "product-description-wrapper"
        ):
            if tag == "div" and attrs.get("class") == "product-description-wrapper":
                self.in_description = True
                self.description_depth = 1
            elif self.in_description:
                self._start_description(tag)
            return

        if tag == "div" and attrs.get("class", "").startswith("stock"):
            self.in_stock_status = True
            return

        if (
            self.in_tier_price_table
            or tag == "table"
            and attrs.get("id") == "tier-price-table"
        ):
            self._start_tier_price(tag, attrs)
            return

        if self.in_specifications or "product-specifications-wrapper" in attrs.get(
            "class", ""
        ):
            self._start_specifications(tag, attrs)

    def handle_data(self, data):
        stripped = data.strip()

        if self.capture_breadcrumb_name and stripped:
            self.breadcrumb_buffer.append(stripped)

        if self.in_description and stripped:
            self.description_buffer.append(stripped)

        if self.in_stock_status and stripped:
            self.stock_buffer.append(stripped)

        if (
            self.in_tier_price_row
            and self.in_tier_price_table
            and stripped
            and not self._tier_price_current_cell_skip
        ):
            if (
                self.tier_cell_index == self.TIER_QUANTITY_INDEX
                and self.tier_quantity is None
            ):
                self.tier_quantity = stripped
            elif (
                self.tier_cell_index == self.TIER_PRICE_PIECE_INDEX
                and self.tier_price_piece is None
            ):
                self.tier_price_piece = stripped
            elif (
                self.tier_cell_index == self.TIER_PRICE_BOX_INDEX
                and self.tier_price_box is None
            ):
                self.tier_price_box = stripped

        if self.in_spec_dl and stripped:
            if self.current_spec_label is None:
                self.spec_label_buffer.append(stripped)
            else:
                self.spec_value_buffer.append(stripped)

    def _end_breadcrumb(self, tag: str) -> None:
        """Handle breadcrumb section end tags."""
        if tag == "span" and self.capture_breadcrumb_name:
            breadcrumb_name = " ".join(self.breadcrumb_buffer).strip()
            if breadcrumb_name and breadcrumb_name not in ("Home", "Products"):
                self.categories.append(breadcrumb_name)
            self.breadcrumb_buffer.clear()
            self.capture_breadcrumb_name = False
        elif tag in ("li", "ul"):
            self.breadcrumb_depth -= 1
        elif tag == "div" and self.breadcrumb_depth == 1:
            self.in_breadcrumbs = False

    def _end_description(self, tag: str) -> None:
        """Handle description section end tags."""
        if tag == "li":
            desc_item = " ".join(self.description_buffer).strip()
            if desc_item:
                if self.description is None:
                    self.description = desc_item
                else:
                    self.description += " | " + desc_item
            self.description_buffer.clear()
            self.description_depth -= 1
        elif tag == "ul":
            self.description_depth -= 1
        elif tag == "div" and self.description_depth == 1:
            self.in_description = False

    def _end_tier_price(self, tag: str) -> None:
        """Handle tier price section end tags."""
        if tag == "td" and self.in_tier_price_row:
            self._tier_price_current_cell_skip = False
        elif tag == "tr" and self.in_tier_price_row:
            if self.tier_quantity and self.tier_price_piece and self.tier_price_box:
                self.price_tiers.append(
                    {
                        "quantity": self.tier_quantity,
                        "price_per_piece": self.tier_price_piece,
                        "price_per_box": self.tier_price_box,
                    }
                )
            self.in_tier_price_row = False
            self.tier_cell_index = 0
        elif tag == "table":
            self.in_tier_price_table = False

    def _end_specifications(self, tag: str) -> None:
        """Handle specifications section end tags."""
        if tag == "dt":
            if self.spec_label_buffer:
                self.current_spec_label = " ".join(self.spec_label_buffer).strip()
        elif tag == "dd":
            if self.current_spec_label and self.spec_value_buffer:
                value = " ".join(self.spec_value_buffer).strip()
                self.specifications[self.current_spec_label] = value
                self.current_spec_label = None
            self.spec_value_buffer = []
        elif tag == "dl":
            self.in_spec_dl = False
            self.current_spec_label = None
        elif tag == "div":
            self.spec_depth -= 1
            if self.spec_depth == 0:
                self.in_specifications = False

    def handle_endtag(self, tag):
        if self.in_breadcrumbs:
            self._end_breadcrumb(tag)
            return

        if self.in_description:
            self._end_description(tag)
            return

        if self.in_stock_status:
            if tag == "div" and self.stock_buffer:
                status_text = " ".join(self.stock_buffer).strip().lower()
                self.stock_available = "in stock" in status_text
                self.stock_buffer.clear()
                self.in_stock_status = False
            return

        if self.in_tier_price_table:
            self._end_tier_price(tag)
            return

        if self.in_specifications:
            self._end_specifications(tag)

    def get_product_data(self) -> dict:
        """Returns the extracted product data."""
        return {
            "categories": self.categories if self.categories else None,
            "description": self.description,
            "stock_available": self.stock_available,
            "price_tiers": self.price_tiers if self.price_tiers else None,
            "specifications": self.specifications if self.specifications else None,
        }
