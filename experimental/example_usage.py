"""
Example usage of the JTL Shop Scraper.

This script demonstrates different ways to use the JTLShopScraper class
to extract product data from asia4friends.de.
"""

import asyncio
import json

from jtl_scraper import JTLShopScraper


async def example_1_simple_scrape() -> None:
    """Example 1: Simple category scraping."""
    print("=" * 70)
    print("EXAMPLE 1: Simple Category Scraping")
    print("=" * 70)

    async with JTLShopScraper() as scraper:
        # Scrape a specific category
        category_url = (
            "https://asia4friends.de/https://asia4friends.de/getraenke/tee-kaffee"
        )

        print(f"\nScraping category: {category_url}\n")

        try:
            products = await scraper.scrape_category(category_url)

            print(f"✓ Found {len(products)} products\n")

            # Display first 5 products
            for product in products[:5]:
                print(f"  Product: {product.name}")
                print(f"  └─ ID: {product.product_id}")
                print(f"  └─ Price: {product.formatted_price}")
                print(f"  └─ URL: {product.url}\n")

            if len(products) > 5:  # noqa: PLR2004
                print(f"  ... and {len(products) - 5} more products")

        except Exception as e:
            print(f"✗ Error: {e}")


async def example_2_with_pagination() -> None:
    """Example 2: Scraping with pagination."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Category Scraping with Pagination")
    print("=" * 70)

    async with JTLShopScraper() as scraper:
        category_url = "https://asia4friends.de/Tee/"

        print(f"\nScraping category (with pagination): {category_url}\n")

        try:
            products = await scraper.scrape_category_paginated(
                category_url, max_pages=3
            )

            print(f"\n✓ Total products found: {len(products)}\n")

            # Summary statistics
            if products:
                prices = [p.price for p in products]
                print("Price Range:")
                print(f"  Min: €{min(prices):.2f}")
                print(f"  Max: €{max(prices):.2f}")
                print(f"  Avg: €{sum(prices) / len(prices):.2f}")

        except Exception as e:
            print(f"✗ Error: {e}")


async def example_3_direct_api_call() -> None:
    """Example 3: Direct API endpoint call (for advanced usage)."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Direct API Endpoint Call")
    print("=" * 70)

    async with JTLShopScraper() as scraper:
        print("\nCalling /io API endpoint with custom parameters...\n")

        try:
            # Example: Fetch compare list (requires comparison products to be set first)
            response = await scraper.call_io_api("updateWishlistDropdown", [])

            print("✓ API Response:")
            print(json.dumps(response, indent=2, ensure_ascii=False)[:500])

        except Exception as e:
            print(f"✗ Error: {e}")
            print("Note: This example may fail if the API endpoint is not available")


async def example_4_save_to_json() -> None:
    """Example 4: Scrape and save products to JSON."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Scrape and Export to JSON")
    print("=" * 70)

    async with JTLShopScraper() as scraper:
        category_url = "https://asia4friends.de/Tee/"

        print("\nScraping and saving to JSON...\n")

        try:
            products = await scraper.scrape_category(category_url)

            # Convert products to JSON-serializable format
            products_data = [
                {
                    "id": p.product_id,
                    "name": p.name,
                    "price": p.price,
                    "formatted_price": p.formatted_price,
                    "url": p.url,
                    "image_url": p.image_url,
                    "description": p.description,
                    "stock_status": p.stock_status,
                }
                for p in products
            ]

            # Save to file
            output_file = "asia4friends_products.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(products_data, f, indent=2, ensure_ascii=False)

            print(f"✓ Saved {len(products)} products to {output_file}")
            print("\nFirst product in JSON format:")
            print(
                json.dumps(
                    products_data[0] if products_data else {},
                    indent=2,
                    ensure_ascii=False,
                )
            )

        except Exception as e:
            print(f"✗ Error: {e}")


async def main() -> None:
    """Run all examples."""
    examples = [
        ("Simple Scraping", example_1_simple_scrape),
        ("Pagination", example_2_with_pagination),
        ("Direct API Call", example_3_direct_api_call),
        ("Export to JSON", example_4_save_to_json),
    ]

    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "JTL SHOP SCRAPER USAGE EXAMPLES" + " " * 23 + "║")
    print("╚" + "=" * 68 + "╝")

    for i, (name, example_func) in enumerate(examples, 1):
        try:
            await example_func()
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
            break
        except Exception as e:
            print(f"\nUnexpected error in example {i} ({name}): {e}\n")

    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
