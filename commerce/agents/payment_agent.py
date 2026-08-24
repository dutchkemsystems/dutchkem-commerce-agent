"""Payment Agent — payment processing and transaction management."""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class PaymentAgent:
    """Handles payment processing, refunds, and payment-related queries."""

    def __init__(self, payment_engine, ecommerce_engine):
        self.payment = payment_engine
        self.ecommerce = ecommerce_engine

    def process(self, message: str, customer_id: str, context: Dict = None) -> Dict[str, Any]:
        msg = message.lower().strip()

        if any(kw in msg for kw in ["pay", "payment", "checkout pay", "complete payment"]):
            return self._initiate_payment(customer_id, context)

        if any(kw in msg for kw in ["refund", "money back"]):
            return self._handle_refund(message, customer_id)

        if any(kw in msg for kw in ["payment method", "saved card", "my cards"]):
            return self._list_payment_methods(customer_id)

        return {"response": "I can help with payments. Try:\n- 'pay' to pay for your order\n- 'refund' to request a refund\n- 'payment methods' to see saved cards", "action": "help"}

    def _initiate_payment(self, customer_id: str, context: Dict = None) -> Dict[str, Any]:
        # Get the latest pending order
        orders = self.ecommerce.get_customer_orders(customer_id, limit=5)
        pending = next((o for o in orders if o["status"] == "pending" and o["payment_status"] == "pending"), None)

        if not pending:
            return {"response": "No pending orders to pay for. Place an order first!", "action": "no_pending"}

        result = self.payment.create_payment_intent(
            amount=pending["total"],
            currency=pending.get("currency", "usd"),
            metadata={"order_id": pending["id"], "customer_id": customer_id},
        )

        if not result.get("success"):
            return {"response": f"Payment initialization failed: {result.get('error', 'Unknown error')}. Please try again.", "action": "payment_error"}

        return {
            "response": (
                f"Payment initiated for order {pending['order_number']}.\n"
                f"Amount: ${pending['total']:.2f}\n"
                f"Payment ID: {result['payment_intent_id']}\n\n"
                f"Please complete payment using the secure payment link."
            ),
            "action": "payment_initiated",
            "payment": result,
            "order": pending,
        }

    def _handle_refund(self, message: str, customer_id: str) -> Dict[str, Any]:
        import re
        order_nums = re.findall(r"ORD-\d+-\w+", message.upper())
        if not order_nums:
            return {"response": "Please provide the order number for your refund request (e.g., 'refund ORD-123-ABC12345').", "action": "need_order"}

        order = self.ecommerce.get_order_by_number(order_nums[0])
        if not order:
            return {"response": "Order not found. Please check the order number.", "action": "order_not_found"}

        if order["payment_status"] != "succeeded":
            return {"response": f"Order {order['order_number']} has not been paid yet. Refunds only apply to paid orders.", "action": "not_paid"}

        if order["status"] == "refunded":
            return {"response": f"Order {order['order_number']} has already been refunded.", "action": "already_refunded"}

        # Create refund
        if order.get("transaction_id"):
            result = self.payment.process_refund(order["transaction_id"], amount=order["total"], reason="customer_request")
            if result.get("success"):
                self.ecommerce.update_order_status(order["id"], "refunded")
                return {
                    "response": f"Refund of ${order['total']:.2f} processed for order {order['order_number']}. It will appear in your account within 5-10 business days.",
                    "action": "refund_processed",
                    "refund": result,
                }
            return {"response": f"Refund failed: {result.get('error')}. Please contact support.", "action": "refund_error"}

        return {"response": "No payment transaction found for this order. Please contact support.", "action": "no_transaction"}

    def _list_payment_methods(self, customer_id: str) -> Dict[str, Any]:
        # In production, look up Stripe customer ID
        return {"response": "Payment methods are managed securely through our payment provider. You can pay with any credit/debit card at checkout.", "action": "payment_methods"}
