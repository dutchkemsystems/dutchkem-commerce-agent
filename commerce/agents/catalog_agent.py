"""Catalog Agent — product browsing, search, and recommendations."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class CatalogAgent:
    """Handles product browsing, search, and recommendation requests."""

    def __init__(self, ecommerce_engine):
        self.ecommerce = ecommerce_engine

    def process(self, message: str, customer_id: str = None, context: Dict = None) -> Dict[str, Any]:
        msg = message.lower().strip()

        # Category browsing
        if any(kw in msg for kw in ["category", "categories", "browse", "list"]):
            cats = self.ecommerce.get_all_categories()
            return {"response": f"Available categories: {', '.join(cats) if cats else 'No categories yet.'}", "action": "categories"}

        # Recommendations
        if any(kw in msg for kw in ["recommend", "suggestion", "popular", "trending"]):
            recs = self.ecommerce.get_recommendations(customer_id, limit=5)
            if recs:
                lines = [f"{i+1}. {p['name']} - ${p['price']:.2f} ({p['rating']:.1f} stars)" for i, p in enumerate(recs)]
                return {"response": "Here are some products you might like:\n" + "\n".join(lines), "action": "recommendations", "products": recs}
            return {"response": "No recommendations available yet. Try browsing our categories!", "action": "recommendations"}

        # Price range search
        if "under" in msg or "below" in msg or "cheap" in msg:
            import re
            nums = re.findall(r"\d+\.?\d*", msg)
            if nums:
                max_price = float(nums[0])
                products = self.ecommerce.search_products("", limit=50)
                affordable = [p for p in products if p["price"] <= max_price][:10]
                if affordable:
                    lines = [f"{i+1}. {p['name']} - ${p['price']:.2f}" for i, p in enumerate(affordable)]
                    return {"response": f"Products under ${max_price:.2f}:\n" + "\n".join(lines), "action": "search", "products": affordable}

        # Default: search with the message
        products = self.ecommerce.search_products(message, limit=10)
        if products:
            lines = [f"{i+1}. {p['name']} - ${p['price']:.2f} ({p['stock_quantity']} in stock)" for i, p in enumerate(products)]
            return {
                "response": f"Found {len(products)} product(s):\n" + "\n".join(lines) + "\n\nReply with a number to see details, or 'add [number]' to add to cart.",
                "action": "search_results",
                "products": products,
            }

        return {"response": "I couldn't find products matching your request. Try different keywords or ask me to show categories.", "action": "no_results"}

    def get_product_detail(self, product_id: str) -> Dict[str, Any]:
        product = self.ecommerce.get_product(product_id)
        if not product:
            return {"response": "Product not found.", "product": None}
        detail = (
            f"**{product['name']}**\n"
            f"Price: ${product['price']:.2f}\n"
            f"Category: {product.get('category', 'N/A')}\n"
            f"Brand: {product.get('brand', 'N/A')}\n"
            f"SKU: {product['sku']}\n"
            f"Rating: {product['rating']:.1f}/5 ({product['reviews_count']} reviews)\n"
            f"In Stock: {'Yes' if product['in_stock'] else 'No'} ({product['stock_quantity']} available)\n\n"
            f"{product.get('description', '')}"
        )
        return {"response": detail, "product": product}
