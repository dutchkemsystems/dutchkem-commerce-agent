"""Sales Agent — shopping cart, checkout, and order placement."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


class SalesAgent:
    """Handles shopping cart operations and order placement."""

    def __init__(self, ecommerce_engine):
        self.ecommerce = ecommerce_engine

    def process(self, message: str, customer_id: str, context: Dict = None) -> Dict[str, Any]:
        msg = message.lower().strip()

        # Add to cart
        if any(kw in msg for kw in ["add", "cart", "buy", "purchase"]):
            return self._handle_add_to_cart(message, customer_id)

        # View cart
        if any(kw in msg for kw in ["cart", "basket", "my items"]):
            return self._view_cart(customer_id)

        # Remove from cart
        if any(kw in msg for kw in ["remove", "delete item", "take out"]):
            return self._handle_remove(message, customer_id)

        # Checkout / place order
        if any(kw in msg for kw in ["checkout", "place order", "proceed", "confirm order"]):
            return self._checkout(customer_id)

        # Order history
        if any(kw in msg for kw in ["order history", "my orders", "past orders"]):
            return self._order_history(customer_id)

        # Wishlist
        if "wishlist" in msg or "save for later" in msg:
            return self._handle_wishlist(message, customer_id)

        return {"response": "I can help you shop! Try:\n- 'add [product] to cart'\n- 'view cart'\n- 'checkout'\n- 'my orders'\n- 'wishlist'", "action": "help"}

    def _handle_add_to_cart(self, message: str, customer_id: str) -> Dict[str, Any]:
        # Try to extract product ID or name from the message
        products = self.ecommerce.search_products(message, limit=5)
        if not products:
            return {"response": "No matching products found. Please try a different search term.", "action": "no_product"}

        # If only one result, add it
        if len(products) == 1:
            try:
                cart = self.ecommerce.add_to_cart(customer_id, products[0]["id"], quantity=1)
                return {
                    "response": f"Added '{products[0]['name']}' to your cart. Cart total: ${cart['total']:.2f} ({cart['count']} items). Reply 'checkout' to place your order.",
                    "action": "added_to_cart",
                    "cart": cart,
                    "product": products[0],
                }
            except ValueError as e:
                return {"response": str(e), "action": "error"}

        # Multiple results — let user choose
        lines = [f"{i+1}. {p['name']} - ${p['price']:.2f}" for i, p in enumerate(products)]
        return {
            "response": "Multiple products found. Which one would you like?\n" + "\n".join(lines) + "\n\nReply with the number to add to cart.",
            "action": "choose_product",
            "products": products,
        }

    def _view_cart(self, customer_id: str) -> Dict[str, Any]:
        cart = self.ecommerce.get_cart(customer_id)
        if not cart.get("items"):
            return {"response": "Your cart is empty. Browse our products and add something you like!", "action": "empty_cart"}

        lines = []
        for i, item in enumerate(cart["items"]):
            lines.append(f"{i+1}. {item['name']} x{item['quantity']} - ${item['total']:.2f}")
        lines.append(f"\n**Cart Total: ${cart['total']:.2f}**")
        lines.append("\nReply 'checkout' to place your order.")

        return {"response": "\n".join(lines), "action": "cart", "cart": cart}

    def _handle_remove(self, message: str, customer_id: str) -> Dict[str, Any]:
        cart = self.ecommerce.get_cart(customer_id)
        if not cart.get("items"):
            return {"response": "Your cart is already empty.", "action": "empty_cart"}

        # Try to find which item
        nums = re.findall(r"\d+", message)
        if nums:
            idx = int(nums[0]) - 1
            if 0 <= idx < len(cart["items"]):
                pid = cart["items"][idx]["product_id"]
                name = cart["items"][idx]["name"]
                self.ecommerce.remove_from_cart(customer_id, pid)
                return {"response": f"Removed '{name}' from your cart.", "action": "removed"}

        return {"response": "Please specify which item to remove (e.g., 'remove 1').", "action": "specify_item"}

    def _checkout(self, customer_id: str) -> Dict[str, Any]:
        try:
            order = self.ecommerce.create_order(customer_id)
            return {
                "response": (
                    f"Order placed! 🎉\n"
                    f"Order Number: {order['order_number']}\n"
                    f"Total: ${order['total']:.2f}\n"
                    f"Status: {order['status']}\n\n"
                    f"Please proceed to payment. Reply 'pay' to complete payment."
                ),
                "action": "order_created",
                "order": order,
            }
        except ValueError as e:
            return {"response": str(e), "action": "checkout_error"}

    def _order_history(self, customer_id: str) -> Dict[str, Any]:
        orders = self.ecommerce.get_customer_orders(customer_id, limit=10)
        if not orders:
            return {"response": "You have no orders yet. Start shopping today!", "action": "no_orders"}

        lines = []
        for o in orders:
            lines.append(f"📦 {o['order_number']} — {o['status']} — ${o['total']:.2f} ({o['created_at'][:10]})")
        return {"response": "Your recent orders:\n" + "\n".join(lines), "action": "orders", "orders": orders}

    def _handle_wishlist(self, message: str, customer_id: str) -> Dict[str, Any]:
        if "add" in message.lower():
            products = self.ecommerce.search_products(message, limit=1)
            if products:
                self.ecommerce.add_to_wishlist(customer_id, products[0]["id"])
                return {"response": f"Added '{products[0]['name']}' to your wishlist.", "action": "wishlist_add"}
        elif "remove" in message.lower():
            products = self.ecommerce.search_products(message, limit=1)
            if products:
                self.ecommerce.remove_from_wishlist(customer_id, products[0]["id"])
                return {"response": f"Removed '{products[0]['name']}' from your wishlist.", "action": "wishlist_remove"}

        return {"response": "Reply 'save [product] to wishlist' or 'remove [product] from wishlist'.", "action": "wishlist_help"}
