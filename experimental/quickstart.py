#!/usr/bin/env python3
"""
Quick start script for the JTL Shop Scraper.

Run this script to quickly test the scraper on asia4friends.de:

    python quickstart.py

This will:
1. Scrape the Tea category
2. Display product information
3. Export results to JSON
"""

import asyncio
import json
import os
import sys
import traceback
from typing import List

# Try importing scraper, with helpful error if not installed
try:
    from jtl_scraper import JTLShopScraper, Product
except ImportError:
    print("❌ Error: 'jtl_scraper' module not found")
    print("\nTo install dependencies, run:")
    print("  pip install -r requirements_scraper.txt")
    sys.exit(1)


async def scrape_and_display() -> List[Product]:
    """Scrape tea category and display results."""

    print("\n" + "=" * 70)
    print("JTL SHOP SCRAPER - QUICK START")
    print("=" * 70)

    category_url = "https://asia4friends.de/themenwelten/koreanische-welt"

    print(f"\n🔍 Scraping category: {category_url}\n")

    try:
        async with JTLShopScraper() as scraper:
            # Fetch products
            products = await scraper.scrape_category(category_url)

            if not products:
                print("❌ No products found. The website structure might have changed.")
                return []

            # Display results
            print(f"✅ Found {len(products)} products\n")
            print("-" * 70)

            for i, product in enumerate(products[:10], 1):
                print(f"\n{i}. {product.name}")
                print(f"   💰 Price: {product.formatted_price}")
                print(f"   🆔 ID: {product.product_id}")
                if product.stock_status:
                    print(f"   📦 Stock: {product.stock_status}")
                if product.image_url:
                    print(f"   🖼  Image: {product.image_url[:60]}...")

            if len(products) > 10:  # noqa: PLR2004
                print(f"\n... and {len(products) - 10} more products")

            print("\n" + "-" * 70)
            return products

    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        print("\nDebug info:")
        print(f"  Error type: {type(e).__name__}")
        print(f"  Error message: {str(e)}")
        return []


def save_to_json(products: List[Product], filename: str = "products.json") -> None:
    """Save products to JSON file."""

    if not products:
        print("\n⚠️  No products to save")
        return

    try:
        data = [
            {
                "id": p.product_id,
                "name": p.name,
                "price": p.price,
                "formatted_price": p.formatted_price,
                "url": p.url,
                "image_url": p.image_url,
                "stock_status": p.stock_status,
                "description": p.description,
            }
            for p in products
        ]

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Saved {len(products)} products to '{filename}'")

        # Show file info

        file_size = os.path.getsize(filename)
        print(f"   File size: {file_size:,} bytes")

        # Show first product as example
        print("\n📋 Example entry:")
        print(json.dumps(data[0], indent=2, ensure_ascii=False))

    except IOError as e:
        print(f"\n❌ Error saving to file: {e}")


def print_summary(products: List[Product]) -> None:
    """Print summary statistics."""

    if not products:
        return

    print("\n" + "=" * 70)
    print("📊 SUMMARY STATISTICS")
    print("=" * 70)

    prices = [p.price for p in products]
    valid_prices = [p for p in prices if p > 0]

    print(f"\nProducts found: {len(products)}")
    print(f"Products with prices: {len(valid_prices)}")

    if valid_prices:
        min_price = min(valid_prices)
        max_price = max(valid_prices)
        avg_price = sum(valid_prices) / len(valid_prices)

        print("\nPrice range:")
        print(f"  💰 Minimum: €{min_price:.2f}")
        print(f"  💰 Maximum: €{max_price:.2f}")
        print(f"  💰 Average:  €{avg_price:.2f}")

    # Product names statistics
    if products:
        name_lengths = [len(p.name) for p in products]
        avg_name_len = sum(name_lengths) / len(name_lengths)
        print("\nProduct names:")
        print(f"  📝 Average length: {avg_name_len:.0f} characters")

    # Stock status
    with_stock = sum(1 for p in products if p.stock_status)
    if with_stock > 0:
        print("\nStock information:")
        print(f"  📦 Products with stock info: {with_stock}")

    # Images
    with_images = sum(1 for p in products if p.image_url)
    print("\nMedia:")
    print(f"  🖼  Products with images: {with_images}")


async def main() -> None:
    """Main entry point."""

    try:
        # Scrape products
        products = await scrape_and_display()

        if products:
            # Save to JSON
            save_to_json(products)

            # Print statistics
            print_summary(products)

        # Final message
        print("\n" + "=" * 70)
        if products:
            print("✅ Scraping completed successfully!")
            print("\n📖 For more examples, see: example_usage.py")
            print("📚 For documentation, see: README_SCRAPER.md")
        else:
            print("❌ Scraping completed but no products were found")
            print("\n💡 Possible solutions:")
            print("  1. Check your internet connection")
            print("  2. Try a different category URL")
            print("  3. Verify the HTML structure hasn't changed")
            print("  4. Check the website terms of service")

        print("=" * 70 + "\n")

    except KeyboardInterrupt:
        print("\n\n⚠️  Scraping interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
