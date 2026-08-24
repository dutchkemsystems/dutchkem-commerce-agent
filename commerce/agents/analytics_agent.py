"""Analytics Agent — business intelligence and customer insights."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List


class AnalyticsAgent:
    """Tracks interactions and provides business analytics."""

    def __init__(self, ecommerce_engine):
        self.ecommerce = ecommerce_engine
        self.events: List[Dict] = []

    def track(self, event_type: str, customer_id: str = None, data: Dict = None):
        self.events.append({
            "type": event_type,
            "customer_id": customer_id,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat(),
        })

    def process(self, message: str, customer_id: str = None, context: Dict = None) -> Dict[str, Any]:
        msg = message.lower().strip()

        if any(kw in msg for kw in ["analytics", "dashboard", "metrics", "report"]):
            return self._get_dashboard()

        if any(kw in msg for kw in ["sales", "revenue", "orders today"]):
            return self._sales_report()

        if any(kw in msg for kw in ["top products", "best selling", "popular products"]):
            return self._top_products()

        return {"response": "I can provide analytics. Try:\n- 'dashboard' for overview\n- 'sales report'\n- 'top products'", "action": "help"}

    def _get_dashboard(self) -> Dict[str, Any]:
        return {
            "response": (
                "📊 **Dashboard Overview**\n\n"
                f"Total Events Tracked: {len(self.events)}\n"
                f"Unique Customers: {len(set(e['customer_id'] for e in self.events if e.get('customer_id')))}\n"
                f"Last Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            ),
            "action": "dashboard",
            "metrics": {
                "total_events": len(self.events),
                "unique_customers": len(set(e["customer_id"] for e in self.events if e.get("customer_id"))),
            },
        }

    def _sales_report(self) -> Dict[str, Any]:
        orders = self.ecommerce.get_customer_orders(None, limit=100) if hasattr(self.ecommerce, "get_customer_orders") else []
        total_revenue = sum(o.get("total", 0) for o in orders)
        return {
            "response": (
                f"💰 **Sales Report**\n\n"
                f"Total Orders: {len(orders)}\n"
                f"Total Revenue: ${total_revenue:.2f}\n"
                f"Average Order Value: ${total_revenue / len(orders):.2f}" if orders else "No orders yet."
            ),
            "action": "sales_report",
        }

    def _top_products(self) -> Dict[str, Any]:
        products = self.ecommerce.search_products("", limit=100) if hasattr(self.ecommerce, "search_products") else []
        products.sort(key=lambda p: p.get("rating", 0) * p.get("reviews_count", 0), reverse=True)
        if products:
            lines = [f"{i+1}. {p['name']} - ${p['price']:.2f} (Rating: {p['rating']:.1f})" for i, p in enumerate(products[:5])]
            return {"response": "🏆 **Top Products**\n" + "\n".join(lines), "action": "top_products"}
        return {"response": "No product data available yet.", "action": "no_data"}
