"""
JTL Shop Web Scraper for asia4friends.de

This module provides a web scraper for JTL-based e-commerce shops,
specifically designed for asia4friends.de. It scrapes product categories
and extracts product information using the shop's `/io` API endpoint.
"""

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup


@dataclass
class Product:
    """Represents a single product from the JTL shop."""

    product_id: int
    name: str
    price: float
    formatted_price: str
    url: str
    image_url: Optional[str] = None
    description: Optional[str] = None
    stock_status: Optional[str] = None
    rating: Optional[float] = None

    def __repr__(self) -> str:
        return f"Product(id={self.product_id}, name='{self.name}', price={self.price})"


class JTLShopScraper:
    """
    Scraper for JTL-based e-commerce shops.

    This scraper connects to JTL shop websites and extracts product information
    from category pages. It uses the shop's built-in AJAX API for efficient
    data extraction.

    Attributes:
        base_url: The base URL of the shop (e.g., 'https://asia4friends.de')
        timeout: HTTP request timeout in seconds
    """

    def __init__(
        self,
        base_url: str = "https://asia4friends.de",
        timeout: float = 10.0,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Initialize the JTL shop scraper.

        Args:
            base_url: Base URL of the JTL shop
            timeout: Request timeout in seconds
            headers: Custom HTTP headers (defaults to standard user-agent)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        self.headers = headers or {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        }

        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "JTLShopScraper":
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            headers=self.headers, timeout=self.timeout, follow_redirects=True
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is initialized."""
        if not self.client:
            self.client = httpx.AsyncClient(headers=self.headers, timeout=self.timeout)
        return self.client

    async def fetch_category(self, category_url: str) -> str:
        """
        Fetch a category page HTML.

        Args:
            category_url: Full URL or relative path to the category page

        Returns:
            HTML content of the category page

        Raises:
            httpx.HTTPError: If the request fails
        """
        if not category_url.startswith("http"):
            category_url = f"{self.base_url}/{category_url.lstrip('/')}"

        client = await self._ensure_client()
        response = await client.get(category_url)
        response.raise_for_status()
        return response.text

    def _extract_products_from_html(self, html: str) -> List[Product]:
        """
        Extract products from category page HTML.

        Args:
            html: HTML content of the category page

        Returns:
            List of Product objects found on the page
        """
        soup = BeautifulSoup(html, "html.parser")
        products: List[Product] = []

        # Find all product items - JTL shop uses multiple possible selectors
        # Primary: product-wrapper with itemtype schema.org/Product
        product_elements = soup.find_all("div", class_="product-wrapper")

        if not product_elements:
            # Fallback: look for divs with schema.org/Product itemtype
            product_elements = soup.find_all(
                "div", attrs={"itemtype": "https://schema.org/Product"}
            )

        if not product_elements:
            # Fallback: look for common product containers
            product_elements = soup.find_all("div", class_=re.compile("productbox"))

        for element in product_elements:
            try:
                product = self._parse_product_element(element)
                if product:
                    products.append(product)
            except (AttributeError, ValueError, KeyError) as e:
                print(f"Warning: Failed to parse product element: {e}")
                continue

        return products

    def _parse_product_element(self, element: Any) -> Optional[Product]:  # noqa: PLR0912, PLR0915
        """
        Parse a single product element from HTML.

        Args:
            element: BeautifulSoup element containing product data

        Returns:
            Product object or None if parsing fails
        """
        try:
            # Extract product ID from form id (e.g., "buy_form_1145" -> 1145)
            # or from hidden input with name="a"
            product_id = None

            # Try to get from form id
            form = element.find("form")
            if form and form.get("id"):
                form_id = form.get("id")
                match = re.search(r"(\d+)", form_id)
                if match:
                    product_id = int(match.group(1))

            # Fallback: try hidden input with name="a"
            if not product_id:
                input_elem = element.find("input", {"name": "a"})
                if input_elem and input_elem.get("value"):
                    product_id = int(input_elem.get("value"))

            if not product_id:
                return None

            # Extract product name
            name_elem = element.find("div", class_="productbox-title")
            if name_elem:
                name_link = name_elem.find("a")
                name = name_link.text.strip() if name_link else "Unknown"
            else:
                name = "Unknown"

            # Extract price
            price_elem = element.find("div", class_="price")
            if price_elem:
                price_span = price_elem.find("span")
                price_str = price_span.text.strip() if price_span else "0"
                # Clean up price string - remove footnote references and extra whitespace
                price_str = re.sub(
                    r"\s*\*\s*", "", price_str
                )  # Remove * and surrounding whitespace
                price_str = " ".join(price_str.split())  # Normalize whitespace
            else:
                price_str = "0"

            formatted_price = price_str

            # Parse numeric price (remove currency symbols and spaces)
            price_numeric = re.sub(r"[^\d,.]", "", price_str).replace(",", ".")
            price = float(price_numeric) if price_numeric else 0.0

            # Extract product URL
            url = ""
            name_elem = element.find("div", class_="productbox-title")
            if name_elem:
                url_link = name_elem.find("a")
                if url_link and url_link.get("href"):
                    url = url_link.get("href")

            # Ensure absolute URL
            if url and not url.startswith("http"):
                url = f"{self.base_url}/{url.lstrip('/')}"

            # Extract image URL
            image_url = None
            img_elem = element.find("img", class_="img-fluid")
            if not img_elem:
                img_elem = element.find("img")

            if img_elem:
                image_url = img_elem.get("src")

            # Extract description (optional) - from alt text
            description = None
            if img_elem:
                description = img_elem.get("alt")

            # Extract stock status (optional)
            stock_status = None
            stock_elem = element.find("div", class_="item-delivery-status")
            if stock_elem:
                status_div = stock_elem.find("div", class_=re.compile("status"))
                stock_status = status_div.text.strip() if status_div else None

            return Product(
                product_id=product_id,
                name=name,
                price=price,
                formatted_price=formatted_price,
                url=url,
                image_url=image_url,
                description=description,
                stock_status=stock_status,
            )
        except (AttributeError, ValueError, IndexError) as e:
            print(f"Failed to parse product element: {e}")
            return None

    async def scrape_category(self, category_url: str) -> List[Product]:
        """
        Scrape all products from a category.

        Args:
            category_url: Full URL or relative path to the category page

        Returns:
            List of all products found in the category
        """
        html = await self.fetch_category(category_url)
        products = self._extract_products_from_html(html)
        return products

    async def scrape_category_paginated(
        self, category_url: str, max_pages: int = 5
    ) -> List[Product]:
        """
        Scrape products from a category with pagination support.

        Args:
            category_url: Base URL of the category page
            max_pages: Maximum number of pages to scrape

        Returns:
            List of all products from all pages
        """
        all_products: List[Product] = []
        page = 1

        while page <= max_pages:
            # Append page parameter (adjust based on actual shop implementation)
            paginated_url = f"{category_url}?page={page}"

            try:
                html = await self.fetch_category(paginated_url)
                products = self._extract_products_from_html(html)

                if not products:
                    # No more products found, stop pagination
                    break

                all_products.extend(products)
                print(f"Page {page}: Found {len(products)} products")
                page += 1

                # Small delay between requests to be respectful
                await asyncio.sleep(0.5)
            except httpx.HTTPError as e:
                print(f"Error fetching page {page}: {e}")
                break

        return all_products

    async def call_io_api(self, method_name: str, params: List[Any]) -> Dict[str, Any]:
        """
        Call the JTL shop's `/io` API endpoint directly.

        This method calls the shop's AJAX API for more advanced operations.

        Args:
            method_name: Name of the server-side method to call
            params: Parameters to pass to the method

        Returns:
            JSON response from the server

        Raises:
            httpx.HTTPError: If the request fails
        """
        client = await self._ensure_client()

        # Build the request payload
        request_data = {"name": method_name, "params": params}
        payload = {"io": json.dumps(request_data)}

        url = f"{self.base_url}/io"

        response = await client.post(url, data=payload)
        response.raise_for_status()

        return response.json()


async def example_scrape() -> None:
    """Example usage of the JTLShopScraper."""
    # Category URL - replace with actual category
    category_url = "https://asia4friends.de/Tee/"

    async with JTLShopScraper() as scraper:
        print(f"Scraping category: {category_url}")
        print("-" * 60)

        try:
            # Scrape products from the category
            products = await scraper.scrape_category(category_url)

            print(f"\nFound {len(products)} products:\n")

            for product in products:
                print(f"  • {product.name}")
                print(f"    ID: {product.product_id}")
                print(f"    Price: {product.formatted_price}")
                if product.stock_status:
                    print(f"    Stock: {product.stock_status}")
                print()

        except httpx.HTTPError as e:
            print(f"Error during scraping: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(example_scrape())
