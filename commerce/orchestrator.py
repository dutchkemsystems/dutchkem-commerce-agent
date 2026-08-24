"""Commerce Orchestrator — the central brain coordinating all commerce agents."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from commerce.agents.analytics_agent import AnalyticsAgent
from commerce.agents.catalog_agent import CatalogAgent
from commerce.agents.inventory_agent import InventoryAgent
from commerce.agents.payment_agent import PaymentAgent
from commerce.agents.sales_agent import SalesAgent
from commerce.agents.shipping_agent import ShippingAgent
from commerce.ecommerce_engine import EcommerceEngine
from commerce.models import DatabaseEngine
from commerce.payment_engine import PaymentEngine
from commerce.shipping_engine import ShippingEngine
from commerce.support_agent import SupportAgent
from commerce.whatsapp_bridge import WhatsAppBridge, WhatsAppMessage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------
INTENT_MAP: Dict[str, List[str]] = {
    "catalog": ["product", "item", "browse", "category", "search", "recommend", "view", "show me", "looking for", "what do you have"],
    "sales": ["buy", "purchase", "order", "cart", "add", "checkout", "place order", "buy now"],
    "payment": ["pay", "payment", "card", "billing", "invoice", "refund", "momo", "m-pesa"],
    "shipping": ["ship", "track", "delivery", "shipping", "package", "where is my order", "when will it arrive"],
    "support": ["help", "problem", "issue", "complaint", "not working", "broken", "return", "exchange", "cancel"],
    "account": ["account", "profile", "password", "login", "register", "sign up", "loyalty", "points"],
    "inventory": ["stock", "available", "in stock", "out of stock", "inventory"],
    "analytics": ["analytics", "dashboard", "report", "sales", "revenue", "metrics"],
    "greeting": ["hello", "hi", "hey", "good morning", "good evening", "good afternoon", "start", "menu"],
    "thanks": ["thank", "thanks", "appreciate"],
}


class CommerceOrchestrator:
    """The main orchestrator that routes messages to the right agent and manages sessions."""

    VERSION = "1.0.0"

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Database
        self.db = DatabaseEngine(config["database_url"])

        # Engines
        self.ecommerce = EcommerceEngine(self.db)
        self.payment = PaymentEngine(
            config.get("stripe_secret_key", ""),
            config.get("stripe_webhook_secret"),
            db=self.db,
        )
        self.shipping = ShippingEngine(config.get("shipping_config", {}))

        # Agents
        self.catalog = CatalogAgent(self.ecommerce)
        self.sales = SalesAgent(self.ecommerce)
        self.payment_agent = PaymentAgent(self.payment, self.ecommerce)
        self.shipping_agent = ShippingAgent(self.shipping, self.ecommerce)
        self.support = SupportAgent(config.get("knowledge_base_path"))
        self.account = CatalogAgent(self.ecommerce)  # placeholder
        self.inventory = InventoryAgent(self.ecommerce)
        self.analytics = AnalyticsAgent(self.ecommerce)

        # WhatsApp bridge
        self.bridge = WhatsAppBridge(
            config.get("whatsapp", {}),
            message_handler=self._on_whatsapp_message,
        )

        # Sessions: phone -> context
        self.sessions: Dict[str, Dict] = {}
        self._agent_map = {
            "catalog": self.catalog,
            "sales": self.sales,
            "payment": self.payment_agent,
            "shipping": self.shipping_agent,
            "support": self.support,
            "account": self.account,
            "inventory": self.inventory,
            "analytics": self.analytics,
        }

        logger.info("Commerce Orchestrator v%s initialized", self.VERSION)

    # ------------------------------------------------------------------
    # Intent classification
    # ------------------------------------------------------------------
    @staticmethod
    def classify_intent(message: str) -> str:
        msg = message.lower().strip()
        for intent, keywords in INTENT_MAP.items():
            for kw in keywords:
                if kw in msg:
                    return intent
        return "general"

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------
    def get_session(self, phone: str) -> Dict:
        if phone not in self.sessions:
            self.sessions[phone] = {
                "phone": phone,
                "customer_id": None,
                "history": [],
                "cart_context": {},
                "last_intent": None,
                "created_at": datetime.utcnow().isoformat(),
            }
        return self.sessions[phone]

    def _update_session(self, phone: str, user_msg: str, bot_reply: str, intent: str):
        session = self.get_session(phone)
        session["history"].append({
            "user": user_msg,
            "bot": bot_reply,
            "intent": intent,
            "timestamp": datetime.utcnow().isoformat(),
        })
        if len(session["history"]) > 50:
            session["history"] = session["history"][-50:]
        session["last_intent"] = intent

    # ------------------------------------------------------------------
    # Message processing
    # ------------------------------------------------------------------
    async def process_message(self, phone: str, content: str, message_id: str = None) -> str:
        """Process an incoming message and return a reply."""
        session = self.get_session(phone)

        # Ensure customer exists
        if not session.get("customer_id"):
            customer = self.ecommerce.get_or_create_customer(phone)
            session["customer_id"] = customer["id"]

        customer_id = session["customer_id"]

        # Classify intent
        intent = self.classify_intent(content)
        self.analytics.track("message_received", customer_id, {"intent": intent, "message": content[:100]})

        # Route to agent
        try:
            reply = await self._route_to_agent(intent, content, customer_id, session)
        except Exception as exc:
            logger.error("Error processing message: %s", exc, exc_info=True)
            reply = "I'm sorry, I encountered an error. Please try again or type 'help' for options."

        # Update session
        self._update_session(phone, content, reply, intent)

        return reply

    async def _route_to_agent(self, intent: str, message: str, customer_id: str, session: Dict) -> str:
        """Route the message to the appropriate agent and return the response text."""
        ctx = {"session": session}

        if intent == "greeting":
            return (
                f"Welcome to our store! 🛍️\n\n"
                "I can help you with:\n"
                "📦 *Products* — 'show me products' or 'search for [item]'\n"
                "🛒 *Shopping* — 'add [product] to cart', 'view cart'\n"
                "💳 *Payments* — 'pay for my order'\n"
                "🚚 *Shipping* — 'track my order'\n"
                "❓ *Support* — 'help with [issue]'\n"
                "👤 *Account* — 'my profile'\n\n"
                "What would you like to do?"
            )

        if intent == "thanks":
            return "You're welcome! Is there anything else I can help you with?"

        if intent == "sales":
            # Handle sales-specific intents
            msg_lower = message.lower()
            if "cart" in msg_lower or "basket" in msg_lower:
                result = self.sales._view_cart(customer_id)
            elif "checkout" in msg_lower or "place order" in msg_lower:
                result = self.sales._checkout(customer_id)
            elif "add" in msg_lower:
                result = self.sales._handle_add_to_cart(message, customer_id)
            elif "remove" in msg_lower:
                result = self.sales._handle_remove(message, customer_id)
            elif "order" in msg_lower and ("history" in msg_lower or "my" in msg_lower):
                result = self.sales._order_history(customer_id)
            else:
                result = self.sales.process(message, customer_id, ctx)
            return result.get("response", "I couldn't process that. Please try again.")

        if intent == "payment":
            result = self.payment_agent.process(message, customer_id, ctx)
            return result.get("response", "Payment processing issue. Please try again.")

        if intent == "shipping":
            result = self.shipping_agent.process(message, customer_id, ctx)
            return result.get("response", "Shipping information unavailable. Please try again.")

        if intent == "support":
            result = self.support.process(message, customer_id, ctx)
            response = result.get("response", "Support request received.")
            if result.get("ticket"):
                response += f"\n\n📋 Ticket: {result['ticket']['id']}"
            return response

        if intent == "account":
            from commerce.agents.account_agent import AccountAgent
            acct = AccountAgent(self.ecommerce)
            result = acct.process(message, customer_id, ctx)
            return result.get("response", "Account info unavailable.")

        if intent == "inventory":
            result = self.inventory.process(message, customer_id, ctx)
            return result.get("response", "Inventory info unavailable.")

        if intent == "analytics":
            result = self.analytics.process(message, customer_id, ctx)
            return result.get("response", "Analytics unavailable.")

        # Default: catalog search
        result = self.catalog.process(message, customer_id, ctx)
        return result.get("response", "I'm not sure how to help with that. Type 'help' for options.")

    # ------------------------------------------------------------------
    # WhatsApp integration
    # ------------------------------------------------------------------
    async def _on_whatsapp_message(self, msg: WhatsAppMessage) -> Optional[str]:
        """Callback for incoming WhatsApp messages."""
        return await self.process_message(msg.sender, msg.text, msg.message_id)

    async def start_whatsapp(self) -> bool:
        """Initialize and start the WhatsApp bridge."""
        return await self.bridge.initialize()

    async def send_whatsapp(self, to: str, text: str) -> bool:
        """Send a WhatsApp message."""
        return await self.bridge.send_message(to, text)

    # ------------------------------------------------------------------
    # Webhook endpoint (for Meta Cloud API)
    # ------------------------------------------------------------------
    async def handle_webhook(self, data: Dict) -> Optional[str]:
        """Handle incoming webhook from Meta Cloud API."""
        msg = await self.bridge.handle_webhook(data)
        if msg:
            reply = await self.process_message(msg.sender, msg.text, msg.message_id)
            await self.send_whatsapp(msg.sender, reply)
            return reply
        return None

    # ------------------------------------------------------------------
    # Analytics & status
    # ------------------------------------------------------------------
    def get_status(self) -> Dict:
        return {
            "version": self.VERSION,
            "whatsapp_connected": self.bridge.connected,
            "sessions": len(self.sessions),
            "tickets": len(self.support.tickets),
            "analytics_events": len(self.analytics.events),
            "uptime": datetime.utcnow().isoformat(),
        }
