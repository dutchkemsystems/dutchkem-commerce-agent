"""Payment Processing Engine — Stripe integration with webhooks."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import stripe

from commerce.models import DatabaseEngine, Order, PaymentTransaction

logger = logging.getLogger(__name__)


class PaymentEngine:
    """Secure payment processing via Stripe with webhook support."""

    def __init__(self, stripe_secret_key: str, webhook_secret: str = None, db: DatabaseEngine = None):
        stripe.api_key = stripe_secret_key
        self.webhook_secret = webhook_secret
        self.db = db

    # ------------------------------------------------------------------
    # Payment Intents
    # ------------------------------------------------------------------
    def create_payment_intent(
        self,
        amount: float,
        currency: str = "usd",
        customer_id: str = None,
        metadata: Dict = None,
    ) -> Dict[str, Any]:
        try:
            params: Dict[str, Any] = {
                "amount": int(amount * 100),
                "currency": currency,
                "automatic_payment_methods": {"enabled": True},
            }
            if customer_id:
                params["customer"] = customer_id
            if metadata:
                params["metadata"] = metadata

            intent = stripe.PaymentIntent.create(**params)

            return {
                "success": True,
                "payment_intent_id": intent.id,
                "client_secret": intent.client_secret,
                "status": intent.status,
                "amount": intent.amount / 100,
                "currency": intent.currency,
            }
        except stripe.error.StripeError as exc:
            logger.error("Stripe create_payment_intent error: %s", exc)
            return {"success": False, "error": str(exc), "error_type": getattr(exc, "type", "api_error")}

    def confirm_payment(self, payment_intent_id: str, payment_method_id: str = None) -> Dict:
        try:
            kwargs = {}
            if payment_method_id:
                kwargs["payment_method"] = payment_method_id
            intent = stripe.PaymentIntent.confirm(payment_intent_id, **kwargs)
            return {
                "success": True,
                "payment_intent_id": intent.id,
                "status": intent.status,
                "amount": intent.amount / 100,
                "currency": intent.currency,
            }
        except stripe.error.StripeError as exc:
            logger.error("Stripe confirm error: %s", exc)
            return {"success": False, "error": str(exc)}

    def retrieve_payment_intent(self, payment_intent_id: str) -> Dict:
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                "success": True,
                "payment_intent_id": intent.id,
                "status": intent.status,
                "amount": intent.amount / 100,
                "currency": intent.currency,
            }
        except stripe.error.StripeError as exc:
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Refunds
    # ------------------------------------------------------------------
    def process_refund(
        self,
        payment_intent_id: str,
        amount: float = None,
        reason: str = None,
    ) -> Dict:
        try:
            params: Dict[str, Any] = {"payment_intent": payment_intent_id}
            if amount:
                params["amount"] = int(amount * 100)
            if reason:
                params["reason"] = reason
            refund = stripe.Refund.create(**params)
            return {
                "success": True,
                "refund_id": refund.id,
                "amount": refund.amount / 100,
                "status": refund.status,
                "payment_intent_id": refund.payment_intent,
            }
        except stripe.error.StripeError as exc:
            logger.error("Stripe refund error: %s", exc)
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Customers
    # ------------------------------------------------------------------
    def create_customer(self, email: str, name: str = None, phone: str = None) -> Dict:
        try:
            params: Dict[str, Any] = {"email": email}
            if name:
                params["name"] = name
            if phone:
                params["phone"] = phone
            customer = stripe.Customer.create(**params)
            return {
                "success": True,
                "customer_id": customer.id,
                "email": customer.email,
                "name": customer.name,
            }
        except stripe.error.StripeError as exc:
            return {"success": False, "error": str(exc)}

    def create_setup_intent(self, customer_id: str) -> Dict:
        try:
            intent = stripe.SetupIntent.create(customer=customer_id)
            return {"success": True, "client_secret": intent.client_secret, "setup_intent_id": intent.id}
        except stripe.error.StripeError as exc:
            return {"success": False, "error": str(exc)}

    def get_payment_methods(self, customer_id: str) -> Dict:
        try:
            pms = stripe.PaymentMethod.list(customer=customer_id, type="card")
            return {
                "success": True,
                "payment_methods": [
                    {
                        "id": pm.id,
                        "brand": pm.card.brand,
                        "last4": pm.card.last4,
                        "exp_month": pm.card.exp_month,
                        "exp_year": pm.card.exp_year,
                    }
                    for pm in pms.data
                ],
            }
        except stripe.error.StripeError as exc:
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Webhook handler
    # ------------------------------------------------------------------
    def handle_webhook(self, payload: bytes, sig_header: str) -> Dict:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, self.webhook_secret)
            event_type = event.type
            data = event.data.object

            # Persist transaction record
            if self.db and event_type in (
                "payment_intent.succeeded",
                "payment_intent.payment_failed",
                "charge.refunded",
            ):
                self._record_transaction(event_type, data)

            return {"success": True, "event_type": event_type, "data": data.to_dict()}
        except ValueError:
            return {"success": False, "error": "Invalid payload"}
        except stripe.error.SignatureVerificationError:
            return {"success": False, "error": "Invalid signature"}

    # ------------------------------------------------------------------
    # DB persistence
    # ------------------------------------------------------------------
    def _record_transaction(self, event_type: str, data: Any):
        s = self.db.get_session()
        try:
            txn = PaymentTransaction()
            txn.stripe_payment_intent_id = getattr(data, "id", None)
            txn.stripe_charge_id = getattr(data, "latest_charge", None)
            txn.amount = getattr(data, "amount", 0) / 100
            txn.currency = getattr(data, "currency", "usd")
            txn.status = event_type.split(".")[-1]
            meta = getattr(data, "metadata", {}) or {}
            txn.order_id = meta.get("order_id")
            txn.customer_id = meta.get("customer_id")
            s.add(txn)
            s.commit()
        except Exception:
            s.rollback()
        finally:
            s.close()
