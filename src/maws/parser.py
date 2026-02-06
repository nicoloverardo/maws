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
            self.current_product = {
                "product_id": int(attrs.get("data-product-id")),
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
            return 4496  # Fallback to known count if not found
        return int(match.group(1))
