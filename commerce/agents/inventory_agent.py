"""Inventory Agent — stock management, alerts, and reordering."""

from __future__ import annotations

from typing import Any, Dict, List


class InventoryAgent:
    """Monitors stock levels, generates alerts, and manages reordering."""

    LOW_STOCK_THRESHOLD = 10

    def __init__(self, ecommerce_engine):
        self.ecommerce = ecommerce_engine
        self.alerts: List[Dict] = []

    def check_stock(self, product_id: str) -> Dict[str, Any]:
        result = self.ecommerce.check_stock(product_id)
        if result.get("available") and result.get("quantity", 0) < self.LOW_STOCK_THRESHOLD:
            self.alerts.append({
                "type": "low_stock",
                "product_id": product_id,
                "quantity": result["quantity"],
            })
        return result

    def get_low_stock_products(self) -> List[Dict]:
        products = self.ecommerce.search_products("", limit=500)
        return [p for p in products if p.get("stock_quantity", 0) < self.LOW_STOCK_THRESHOLD]

    def process(self, message: str, customer_id: str = None, context: Dict = None) -> Dict[str, Any]:
        msg = message.lower().strip()

        if any(kw in msg for kw in ["stock", "inventory", "in stock"]):
            return self._check_stock_query(message)

        if any(kw in msg for kw in ["low stock", "out of stock", "alerts"]):
            return self._low_stock_report()

        if any(kw in msg for kw in ["reorder", "restock"]):
            return self._reorder_suggestions()

        return {"response": "I can help with inventory. Try:\n- 'check stock for [product]'\n- 'low stock report'\n- 'reorder suggestions'", "action": "help"}

    def _check_stock_query(self, message: str) -> Dict[str, Any]:
        products = self.ecommerce.search_products(message, limit=5)
        if products:
            lines = [f"{p['name']} ({p['sku']}): {p['stock_quantity']} in stock {'✅' if p['in_stock'] else '❌'}" for p in products]
            return {"response": "Stock levels:\n" + "\n".join(lines), "action": "stock_check"}
        return {"response": "No matching products found.", "action": "no_products"}

    def _low_stock_report(self) -> Dict[str, Any]:
        low = self.get_low_stock_products()
        if low:
            lines = [f"⚠️ {p['name']} ({p['sku']}): {p['stock_quantity']} remaining" for p in low[:10]]
            return {"response": "Low Stock Alert:\n" + "\n".join(lines), "action": "low_stock", "products": low}
        return {"response": "All products are well-stocked!", "action": "no_alerts"}

    def _reorder_suggestions(self) -> Dict[str, Any]:
        low = self.get_low_stock_products()
        if low:
            lines = [f"📦 {p['name']} - Current: {p['stock_quantity']}, Suggest reorder: 50 units" for p in low[:10]]
            return {"response": "Reorder Suggestions:\n" + "\n".join(lines), "action": "reorder", "products": low}
        return {"response": "No reordering needed at this time.", "action": "no_reorder"}
