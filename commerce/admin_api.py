"""Admin Dashboard & REST API for the WhatsApp Commerce Agent."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

from flask import Flask, g, jsonify, request

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_commerce_orchestrator = None


def create_app(orchestrator=None) -> Flask:
    """Create and configure the Flask admin dashboard."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    global _commerce_orchestrator
    if orchestrator:
        _commerce_orchestrator = orchestrator

    def _get_orch():
        global _commerce_orchestrator
        if _commerce_orchestrator is None:
            from commerce.orchestrator import CommerceOrchestrator
            from dotenv import load_dotenv
            load_dotenv()
            _commerce_orchestrator = CommerceOrchestrator(_build_config())
        return _commerce_orchestrator

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------
    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "version": "1.0.0"})

    @app.route("/api/status")
    def status():
        orch = _get_orch()
        return jsonify(orch.get_status())

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------
    @app.route("/api/products", methods=["GET"])
    def list_products():
        orch = _get_orch()
        query = request.args.get("q", "")
        category = request.args.get("category")
        limit = int(request.args.get("limit", 20))

        if category:
            products = orch.ecommerce.get_category_products(category, limit=limit)
        elif query:
            products = orch.ecommerce.search_products(query, limit=limit)
        else:
            products = orch.ecommerce.search_products("", limit=limit)
        return jsonify({"products": products, "count": len(products)})

    @app.route("/api/products/<product_id>", methods=["GET"])
    def get_product(product_id):
        orch = _get_orch()
        product = orch.ecommerce.get_product(product_id)
        if not product:
            return jsonify({"error": "Not found"}), 404
        return jsonify(product)

    @app.route("/api/products", methods=["POST"])
    def create_product():
        orch = _get_orch()
        data = request.get_json(force=True)
        product = orch.ecommerce.create_product(data)
        return jsonify(product), 201

    @app.route("/api/products/<product_id>", methods=["PUT"])
    def update_product(product_id):
        orch = _get_orch()
        data = request.get_json(force=True)
        product = orch.ecommerce.update_product(product_id, data)
        if not product:
            return jsonify({"error": "Not found"}), 404
        return jsonify(product)

    # ------------------------------------------------------------------
    # Customers
    # ------------------------------------------------------------------
    @app.route("/api/customers", methods=["GET"])
    def list_customers():
        orch = _get_orch()
        # Placeholder — in production, paginate from DB
        return jsonify({"customers": [], "count": 0})

    @app.route("/api/customers/<customer_id>", methods=["GET"])
    def get_customer(customer_id):
        orch = _get_orch()
        profile = orch.ecommerce.get_or_create_customer(customer_id)
        return jsonify(profile)

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------
    @app.route("/api/orders", methods=["GET"])
    def list_orders():
        orch = _get_orch()
        customer_id = request.args.get("customer_id")
        if customer_id:
            orders = orch.ecommerce.get_customer_orders(customer_id)
        else:
            orders = []
        return jsonify({"orders": orders, "count": len(orders)})

    @app.route("/api/orders/<order_id>", methods=["GET"])
    def get_order(order_id):
        orch = _get_orch()
        order = orch.ecommerce.get_order(order_id)
        if not order:
            return jsonify({"error": "Not found"}), 404
        return jsonify(order)

    @app.route("/api/orders/<order_id>/status", methods=["PUT"])
    def update_order_status(order_id):
        orch = _get_orch()
        data = request.get_json(force=True)
        try:
            order = orch.ecommerce.update_order_status(order_id, data["status"])
            return jsonify(order)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    # ------------------------------------------------------------------
    # Payments
    # ------------------------------------------------------------------
    @app.route("/api/payments/create-intent", methods=["POST"])
    def create_payment():
        orch = _get_orch()
        data = request.get_json(force=True)
        result = orch.payment.create_payment_intent(
            amount=data["amount"],
            currency=data.get("currency", "usd"),
            customer_id=data.get("customer_id"),
            metadata=data.get("metadata"),
        )
        return jsonify(result)

    @app.route("/api/payments/webhook", methods=["POST"])
    def payment_webhook():
        orch = _get_orch()
        sig = request.headers.get("Stripe-Signature", "")
        result = orch.payment.handle_webhook(request.data, sig)
        return jsonify(result)

    # ------------------------------------------------------------------
    # Shipping
    # ------------------------------------------------------------------
    @app.route("/api/shipping/rates", methods=["POST"])
    def shipping_rates():
        orch = _get_orch()
        data = request.get_json(force=True)
        rates = orch.shipping.get_rates(data["origin"], data["destination"], data["package"])
        return jsonify({"rates": rates})

    @app.route("/api/shipping/track/<tracking_number>", methods=["GET"])
    def track_shipment(tracking_number):
        orch = _get_orch()
        result = orch.shipping.track(tracking_number)
        return jsonify(result)

    # ------------------------------------------------------------------
    # Support tickets
    # ------------------------------------------------------------------
    @app.route("/api/tickets", methods=["GET"])
    def list_tickets():
        orch = _get_orch()
        status = request.args.get("status")
        tickets = orch.support.list_tickets(status)
        return jsonify({"tickets": tickets, "count": len(tickets)})

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------
    @app.route("/api/analytics", methods=["GET"])
    def analytics():
        orch = _get_orch()
        return jsonify({
            "events": len(orch.analytics.events),
            "sessions": len(orch.sessions),
            "tickets": len(orch.support.tickets),
        })

    # ------------------------------------------------------------------
    # WhatsApp webhook verification (Meta)
    # ------------------------------------------------------------------
    @app.route("/webhook/whatsapp", methods=["GET"])
    def whatsapp_verify():
        verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "commerce-verify-token")
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == verify_token:
            return challenge, 200
        return "Forbidden", 403

    @app.route("/webhook/whatsapp", methods=["POST"])
    async def whatsapp_webhook():
        orch = _get_orch()
        data = request.get_json(force=True)
        await orch.handle_webhook(data)
        return "OK", 200

    # ------------------------------------------------------------------
    # Dashboard (simple HTML)
    # ------------------------------------------------------------------
    @app.route("/")
    def dashboard():
        return """
        <!DOCTYPE html>
        <html>
        <head><title>WhatsApp Commerce Agent — Admin</title></head>
        <body>
            <h1>🛍️ WhatsApp Commerce Agent</h1>
            <h2>API Endpoints</h2>
            <ul>
                <li><a href="/health">/health</a> — Health check</li>
                <li><a href="/api/status">/api/status</a> — System status</li>
                <li><a href="/api/products">/api/products</a> — Products</li>
                <li><a href="/api/orders">/api/orders</a> — Orders</li>
                <li><a href="/api/tickets">/api/tickets</a> — Support Tickets</li>
                <li><a href="/api/analytics">/api/analytics</a> — Analytics</li>
            </ul>
            <p>WhatsApp Webhook: <code>POST /webhook/whatsapp</code></p>
            <p>Payment Webhook: <code>POST /api/payments/webhook</code></p>
        </body>
        </html>
        """, 200

    return app


def _build_config() -> Dict[str, Any]:
    """Build config dict from environment variables."""
    return {
        "database_url": os.getenv("DATABASE_URL", "sqlite:///commerce.db"),
        "stripe_secret_key": os.getenv("STRIPE_SECRET_KEY", ""),
        "stripe_webhook_secret": os.getenv("STRIPE_WEBHOOK_SECRET"),
        "knowledge_base_path": os.getenv("KNOWLEDGE_BASE_PATH"),
        "whatsapp": {
            "provider": os.getenv("WHATSAPP_PROVIDER", "mock"),
            "phone_number_id": os.getenv("WHATSAPP_PHONE_NUMBER_ID"),
            "access_token": os.getenv("WHATSAPP_ACCESS_TOKEN"),
            "verify_token": os.getenv("WHATSAPP_VERIFY_TOKEN"),
            "api_version": os.getenv("WHATSAPP_API_VERSION", "v18.0"),
        },
        "shipping_config": {
            "fedex": {
                "api_key": os.getenv("FEDEX_API_KEY", ""),
                "secret_key": os.getenv("FEDEX_SECRET_KEY", ""),
                "account_number": os.getenv("FEDEX_ACCOUNT_NUMBER", ""),
                "meter_number": os.getenv("FEDEX_METER_NUMBER", ""),
                "test_mode": os.getenv("FEDEX_TEST_MODE", "true").lower() == "true",
            },
            "ups": {
                "api_key": os.getenv("UPS_API_KEY", ""),
                "username": os.getenv("UPS_USERNAME", ""),
                "password": os.getenv("UPS_PASSWORD", ""),
                "test_mode": os.getenv("UPS_TEST_MODE", "true").lower() == "true",
            },
            "default_provider": os.getenv("DEFAULT_SHIPPING_PROVIDER", "fedex"),
        },
    }


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("COMMERCE_PORT", "8080")), debug=True)
