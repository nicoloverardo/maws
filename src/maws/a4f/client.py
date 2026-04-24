import asyncio
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, Field, field_validator
from tqdm.asyncio import tqdm_asyncio

# ------------------------
# DATA MODEL
# ------------------------


class ProductModel(BaseModel):
    """Product model representing a scraped product with metadata."""

    artikel_id: str
    name: Optional[str] = None
    brand: Optional[str] = None
    price: Optional[str] = None
    product_url: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    stock_status: Optional[str] = None
    variants: List[Dict[str, Any]] = Field(default_factory=list)

    @field_validator("product_url", "image_url", mode="before")
    @classmethod
    def validate_urls(cls, v: Any) -> Optional[str]:
        """Convert URLs to strings, handling both str and HttpUrl types."""
        if v is None:
            return None
        return str(v)


# ------------------------
# SCRAPER
# jtl.io.js and jtl.article.js reverse-engineered
# https://asia4friends.de/templates/Mas5/js/jtl.article.js?v=1.0.1
# https://asia4friends.de/templates/Mas5/js/jtl.io.js?v=1.0.1
# ------------------------


class JTLScraper:
    """
    Async scraper for JTL-based e-commerce shops.

    Combines HTML parsing with the JTL /io API for comprehensive product data extraction.
    """

    def __init__(
        self,
        base_url: str = "https://asia4friends.de",
        max_connections: int = 20,
        rate_limit: float = 0.05,
    ) -> None:
        """
        Initialize the scraper.

        Args:
            base_url: Base URL of the JTL shop
            max_connections: Maximum concurrent HTTP connections
            rate_limit: Delay between requests in seconds
        """
        self.base_url = base_url.rstrip("/")
        # Start with standard headers for initial page fetching
        # XMLHttpRequest header is added later for API calls
        self.client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=max_connections),
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            follow_redirects=True,
            timeout=10.0,
        )
        self.token: Optional[str] = None
        self.rate_limit = rate_limit

    async def init(self) -> None:
        """Initialize scraper by extracting JTL token from homepage."""
        try:
            r = await self.client.get(self.base_url)
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise ValueError(
                f"Failed to fetch homepage ({self.base_url}): {e}\n"
                "Check your internet connection and verify the URL is correct."
            ) from e

        # Try to extract the token
        match = re.search(r'name="jtl_token" value="([^"]+)"', r.text)

        if not match:
            # Provide more debugging info
            has_jtl_token_attr = "jtl_token" in r.text
            html_size = len(r.text)

            error_details = (
                f"Failed to extract JTL token from homepage.\n"
                f"  URL: {self.base_url}\n"
                f"  Status: {r.status_code}\n"
                f"  HTML size: {html_size} bytes\n"
                f"  Contains 'jtl_token': {has_jtl_token_attr}\n"
            )

            if has_jtl_token_attr:
                # Show the context around the token
                idx = r.text.find("jtl_token")
                context = r.text[max(0, idx - 50) : min(len(r.text), idx + 200)]
                error_details += f"\n  Context: ...{context}..."

            raise ValueError(error_details)

        self.token = match.group(1)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        await asyncio.sleep(self.rate_limit)

    # ------------------------
    # RPC
    # ------------------------

    async def call(self, name: str, params: List[Any]) -> Dict[str, Any]:
        """
        Call the JTL /io API endpoint.

        Args:
            name: Method name to call
            params: Parameters for the method

        Returns:
            JSON response from the API
        """
        await self._rate_limit()

        payload = {"name": name, "params": params}

        # Add XMLHttpRequest header for API calls
        headers = {"x-requested-with": "XMLHttpRequest"}

        r = await self.client.post(
            f"{self.base_url}/io",
            data={"io": json.dumps(payload)},
            headers=headers,
        )

        return r.json()

    def extract_var_assigns(self, resp: Dict[str, Any]) -> Dict[str, Any]:
        """Extract variable assignments from API response."""
        data = {}
        for v in resp.get("varAssigns", []):
            data[v["name"]] = v["value"]
        return data

    # ------------------------
    # HTML PARSING
    # ------------------------

    def _extract_products_from_html(self, html: str) -> List[ProductModel]:
        """
        Extract products from category page HTML.

        Args:
            html: HTML content of the category page

        Returns:
            List of Product models found on the page
        """
        soup = BeautifulSoup(html, "html.parser")
        products: List[ProductModel] = []

        # JTL shop product structure: div.productbox with buy_form inside
        # Find all product containers
        product_elements = soup.find_all("div", class_="productbox")

        for element in product_elements:
            try:
                product = self._parse_product_element(element)
                if product:
                    products.append(product)
            except (AttributeError, ValueError, KeyError):
                # Skip malformed product elements
                continue

        return products

    def _parse_product_element(self, element: Tag) -> Optional[ProductModel]:  # noqa: PLR0912, PLR0915
        """
        Parse a single product element from HTML.

        Args:
            element: BeautifulSoup element containing product data

        Returns:
            Product object or None if parsing fails
        """
        try:
            # Extract product ID from the form id (e.g., "buy_form_1145" -> 1145)
            product_id: Optional[str] = None

            # Try to get from form id
            form = element.find("form", {"id": re.compile(r"buy_form_\d+")})
            if form and form.get("id"):
                form_id = form.get("id")
                match = re.search(r"buy_form_(\d+)", form_id)
                if match:
                    product_id = match.group(1)

            # Fallback: try hidden input with name="a"
            if not product_id:
                input_elem = element.find("input", {"name": "a"})
                if input_elem and input_elem.get("value"):
                    product_id = str(input_elem.get("value"))

            if not product_id:
                return None

            # Extract product name from div.productbox-title > a
            name: Optional[str] = None
            name_elem = element.find("div", class_="productbox-title")
            if name_elem:
                name_link = name_elem.find("a")
                if name_link:
                    name = name_link.get_text(strip=True)

            if not name:
                name = None

            # Extract price from div.price or div.productbox-price
            price_str = "0"
            price_elem = element.find("div", class_="price")
            if not price_elem:
                price_elem = element.find("div", class_="productbox-price")

            if price_elem:
                price_span = price_elem.find("span")
                if price_span:
                    price_str = price_span.get_text(strip=True)
                    # Clean up price string - remove footnote references and extra whitespace
                    price_str = re.sub(r"\s*\*\s*", "", price_str)
                    price_str = " ".join(price_str.split())

            formatted_price = price_str

            # Extract product URL from div.productbox-title > a
            url: Optional[str] = None
            if name_elem:
                url_link = name_elem.find("a")
                if url_link and url_link.get("href"):
                    url = urljoin(self.base_url, str(url_link.get("href")))

            # Extract image URL
            image_url: Optional[str] = None
            img_elem = element.find("img", class_="img-fluid")
            if not img_elem:
                img_elem = element.find("img")

            if img_elem and img_elem.get("src"):
                image_url = urljoin(self.base_url, str(img_elem.get("src")))

            # Extract description from alt text
            description: Optional[str] = None
            if img_elem and img_elem.get("alt"):
                description = img_elem.get("alt")

            # Extract stock status (optional)
            stock_status: Optional[str] = None
            stock_elem = element.find("div", class_="item-delivery-status")
            if stock_elem:
                status_div = stock_elem.find("div", class_=re.compile("status"))
                if status_div:
                    stock_status = status_div.get_text(strip=True)

            return ProductModel(
                artikel_id=product_id,
                name=name,
                price=formatted_price,
                product_url=url,
                image_url=image_url,
                description=description,
                stock_status=stock_status,
            )
        except (AttributeError, ValueError, IndexError):
            return None

    # ------------------------
    # CATEGORY + PAGINATION
    # ------------------------

    async def get_categories(self) -> List[str]:
        """Fetch all product subcategory URLs from the navbar.

        Products are only available in subcategories, not in main categories.
        Extracts subcategory links from each main category's dropdown menu.
        """
        # Fetch the homepage to get the navbar
        html = (await self.client.get(self.base_url)).text
        soup = BeautifulSoup(html, "html.parser")

        product_categories = set()

        # Find all main category toggle links in the navbar
        main_categories = soup.find_all("a", class_="dropdown-toggle")

        for main_cat in main_categories:
            # Get the dropdown-menu that comes after this toggle
            dropdown_menu = main_cat.find_next_sibling("ul", class_="dropdown-menu")

            if dropdown_menu:
                # Find all nav-item li elements that are NOT dropdowns (these are subcategories)
                subcategory_items = dropdown_menu.find_all(
                    "li", class_="nav-item", recursive=False
                )

                for sub_item in subcategory_items:
                    # Skip items with the dropdown class (those are just back-links to main)
                    if "dropdown" in sub_item.get("class", []):
                        continue

                    # Get the link from this subcategory item
                    sub_link = sub_item.find("a")
                    if sub_link:
                        sub_href = sub_link.get("href", "").strip()
                        if (
                            sub_href
                            and sub_href.startswith(self.base_url)
                            and sub_href != self.base_url
                        ):
                            product_categories.add(sub_href)

        return list(sorted(product_categories))

    async def get_products_from_category(
        self, category_url: str, max_pages: int = 25
    ) -> List[ProductModel]:
        """
        Get products from a category using the JTL API.

        Args:
            category_url: URL of the category page
            max_pages: Maximum number of pages to fetch (default 2 for testing)

        Returns:
            List of all products in the category
        """
        all_products: List[ProductModel] = []

        for page in range(1, max_pages + 1):
            try:
                # Build the pagination URL
                url = f"{category_url}?p={page}"
                print(f"Fetching page {page}: {url}", flush=True)

                # Fetch the HTML
                html = (await self.client.get(url)).text

                # Extract products from HTML
                products = self._extract_products_from_html(html)

                if not products:
                    # No more products found, stop pagination
                    print(f"No products found on page {page}, stopping", flush=True)
                    break

                print(f"✓ Page {page}: {len(products)} products", flush=True)
                all_products.extend(products)

                # Small delay between requests
                await asyncio.sleep(0.1)
            except httpx.HTTPError as e:
                print(f"Error fetching page {page}: {e}", flush=True)
                break

        return all_products

    def extract_product_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract product ID from product URL.

        Args:
            url: Product URL

        Returns:
            Product ID or None if extraction fails
        """
        # Try to extract ID from the end of the URL path
        match = re.search(r"(\d+)(?:[/#?]|$)", url)
        return match.group(1) if match else None

    # ------------------------
    # VARIATION GRAPH TRAVERSAL
    # ------------------------

    async def resolve_variations(
        self, artikel_id: str, base_combo: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Resolve all product variations using dependency-aware traversal.

        Args:
            artikel_id: Article ID of the product
            base_combo: Starting combination (empty dict if None)

        Returns:
            List of all possible variation combinations
        """
        if base_combo is None:
            base_combo = {}

        visited: List[Dict[str, Any]] = []
        stack: List[Dict[str, str]] = [base_combo]

        while stack:
            combo = stack.pop()

            resp = await self.call(
                "checkVarkombiDependencies",
                [
                    {
                        "jtl_token": self.token,
                        "VariKindArtikel": artikel_id,
                        "eigenschaftwert": combo,
                        "anzahl": "1",
                    }
                ],
            )

            data = self.extract_var_assigns(resp)

            visited.append({"combo": combo, "data": data})

            # Try to expand combinations if possible
            next_variations = data.get("variationValues") or {}

            for key, values in next_variations.items():
                for v in values:
                    new_combo = combo.copy()
                    new_combo[str(key)] = str(v)

                    if new_combo not in [x["combo"] for x in visited]:
                        stack.append(new_combo)

        return visited

    # ------------------------
    # PRODUCT PIPELINE
    # ------------------------

    async def process_product(
        self, artikel_id: str, product_url: str
    ) -> Optional[ProductModel]:
        """
        Process a single product by fetching details from the API.

        Args:
            artikel_id: Product article ID
            product_url: Product URL

        Returns:
            Product model with details and variants, or None if processing fails
        """
        try:
            base_resp = await self.call("getProductDetails", [artikel_id])
            base = self.extract_var_assigns(base_resp)

            variants = await self.resolve_variations(artikel_id)

            return ProductModel(
                artikel_id=artikel_id,
                name=base.get("cName"),
                brand=base.get("cBrand"),
                price=base.get("cPrice"),
                product_url=product_url,
                image_url=base.get("cImage"),
                description=base.get("cDescription"),
                variants=variants,
            )

        except Exception as e:
            print(f"[ERROR] {artikel_id}: {e}")
            return None

    # ------------------------
    # MAIN
    # ------------------------

    async def scrape_all(self) -> List[ProductModel]:
        """
        Scrape all products from all categories.

        Returns:
            List of all scraped products
        """
        await self.init()

        categories = await self.get_categories()
        print(f"Found {len(categories)} categories")

        cat_tasks = [self.get_products_from_category(c) for c in categories]
        cat_results = await tqdm_asyncio.gather(*cat_tasks)

        all_products: List[ProductModel] = []
        for r in cat_results:
            all_products.extend(r)

        print(f"Found {len(all_products)} products from HTML parsing")

        return all_products


# ------------------------
# SAVE JSON
# ------------------------


def save_to_json(
    products: List[ProductModel],
    folder_path: Optional[Path] = None,
    filename: str = "products.json",
) -> None:
    """
    Save products to JSON file.

    Args:
        products: List of Product models to save
        folder_path: Directory to save the file (defaults to current directory)
        filename: Name of the output file
    """
    if folder_path is None:
        folder_path = Path.cwd()

    folder_path.mkdir(parents=True, exist_ok=True)

    with open(folder_path / filename, "w", encoding="utf-8") as f:
        json.dump(
            [p.model_dump() for p in products],
            f,
            ensure_ascii=False,
            indent=2,
        )


# ------------------------
# RUN
# ------------------------


async def main(folder_path: Optional[Path] = None) -> None:
    """
    Main scraper entry point.

    Args:
        folder_path: Directory to save results
    """
    scraper = JTLScraper("https://asia4friends.de", max_connections=20, rate_limit=0.05)

    try:
        products = await scraper.scrape_all()

        print(f"\nScraped {len(products)} products")

        save_to_json(products, folder_path=folder_path)

    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
