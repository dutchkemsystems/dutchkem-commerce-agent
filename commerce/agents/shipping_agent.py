"""Shipping Agent — shipping queries, tracking, and label generation."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ShippingAgent:
    """Handles shipping queries, rate calculation, tracking, and label generation."""

    def __init__(self, shipping_engine, ecommerce_engine):
        self.shipping = shipping_engine
        self.ecommerce = ecommerce_engine

    def process(self, message: str, customer_id: str = None, context: Dict = None) -> Dict[str, Any]:
        msg = message.lower().strip()

        if any(kw in msg for kw in ["track", "tracking", "where is", "delivery status"]):
            return self._track_shipment(message, customer_id)

        if any(kw in msg for kw in ["shipping cost", "shipping rate", "how much shipping", "delivery cost"]):
            return self._get_shipping_rates(message, context)

        if any(kw in msg for kw in ["ship", "send", "deliver"]):
            return self._create_shipment(message, context)

        return {"response": "I can help with shipping. Try:\n- 'track [order number]'\n- 'shipping cost for [order]'\n- 'ship [order]'", "action": "help"}

    def _track_shipment(self, message: str, customer_id: str = None) -> Dict[str, Any]:
        # Try to find tracking number or order number in message
        tracking_nums = re.findall(r"\b\d{12,22}\b", message)
        order_nums = re.findall(r"ORD-\d+-\w+", message.upper())

        if tracking_nums:
            result = self.shipping.track(tracking_nums[0])
            if result.get("success"):
                return {
                    "response": (
                        f"Tracking: {tracking_nums[0]}\n"
                        f"Status: {result.get('status', 'Unknown')}\n"
                        f"Estimated Delivery: {result.get('estimated_delivery', 'N/A')}\n"
                        f"Last Update: {result.get('last_update', 'N/A')}"
                    ),
                    "action": "tracking",
                    "tracking": result,
                }
            return {"response": f"Could not track package: {result.get('error', 'Unknown error')}", "action": "track_error"}

        if order_nums:
            order = self.ecommerce.get_order_by_number(order_nums[0])
            if order and order.get("shipping_tracking", {}).get("tracking_number"):
                tn = order["shipping_tracking"]["tracking_number"]
                return self._track_shipment(f"track {tn}", customer_id)
            elif order:
                return {"response": f"Order {order['order_number']} status: {order['status']}. Tracking number not yet assigned.", "action": "no_tracking"}
            return {"response": "Order not found.", "action": "not_found"}

        if customer_id:
            orders = self.ecommerce.get_customer_orders(customer_id, limit=5)
            for o in orders:
                if o.get("shipping_tracking", {}).get("tracking_number"):
                    return self._track_shipment(f"track {o['shipping_tracking']['tracking_number']}", customer_id)
            return {"response": "No shipments found for your recent orders.", "action": "no_shipments"}

        return {"response": "Please provide an order number or tracking number.", "action": "need_number"}

    def _get_shipping_rates(self, message: str, context: Dict = None) -> Dict[str, Any]:
        origin = context.get("origin", {"street": "123 Main St", "city": "New York", "state": "NY", "postal_code": "10001", "country": "US"}) if context else {"street": "123 Main St", "city": "New York", "state": "NY", "postal_code": "10001", "country": "US"}
        destination = context.get("destination", {"street": "456 Oak Ave", "city": "Los Angeles", "state": "CA", "postal_code": "90001", "country": "US"}) if context else {"street": "456 Oak Ave", "city": "Los Angeles", "state": "CA", "postal_code": "90001", "country": "US"}
        package = context.get("package", {"weight": 2, "length": 10, "width": 8, "height": 6})

        rates = self.shipping.get_rates(origin, destination, package)
        if rates:
            lines = [f"{r['service_name']} ({r['service_type']}): ${r['total_charge']:.2f}" for r in rates[:5]]
            return {"response": "Shipping rates:\n" + "\n".join(lines), "action": "rates", "rates": rates}

        return {"response": "Could not retrieve shipping rates. Please try again later.", "action": "rates_error"}

    def _create_shipment(self, message: str, context: Dict = None) -> Dict[str, Any]:
        if not context:
            return {"response": "Shipment details required (origin, destination, package info).", "action": "need_context"}

        result = self.shipping.create_shipment(
            context.get("origin", {}),
            context.get("destination", {}),
            context.get("package", {}),
            context.get("service"),
        )

        if result.get("success"):
            return {
                "response": (
                    f"Shipment created!\n"
                    f"Tracking: {result.get('tracking_number')}\n"
                    f"Label: {result.get('label_url', 'N/A')}\n"
                    f"Shipment ID: {result.get('shipment_id')}"
                ),
                "action": "shipment_created",
                "shipment": result,
            }

        return {"response": f"Shipment creation failed: {result.get('error')}", "action": "shipment_error"}
