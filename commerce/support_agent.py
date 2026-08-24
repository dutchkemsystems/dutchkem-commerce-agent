"""Customer Support Agent — AI-powered support with sentiment analysis and ticketing."""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SupportAgent:
    """Intelligent customer support with FAQ, sentiment analysis, and ticket creation."""

    def __init__(self, kb_path: str = None, llm=None):
        self.llm = llm
        self.kb = self._load_kb(kb_path)
        self.faq = self._build_faq()
        self.tickets: Dict[str, Dict] = {}

    # ------------------------------------------------------------------
    # Knowledge base
    # ------------------------------------------------------------------
    def _load_kb(self, path: str = None) -> Dict:
        if path and Path(path).exists():
            try:
                return json.loads(Path(path).read_text(encoding="utf-8"))
            except Exception:
                pass
        return self._default_kb()

    @staticmethod
    def _default_kb() -> Dict:
        return {
            "orders": {
                "tracking": "You can track your order using the tracking number sent to your email or WhatsApp. Reply with 'track my order' and I'll look it up.",
                "status": "To check your order status, reply with 'order status' and your order number.",
                "return": "Our return policy allows returns within 30 days of delivery. Contact us to initiate a return.",
                "cancel": "Orders can be cancelled within 1 hour of placement. After that, please contact support.",
                "exchange": "We offer exchanges within 14 days of delivery. The item must be unused and in original packaging.",
            },
            "payments": {
                "methods": "We accept credit/debit cards, mobile money (M-Pesa, MTN, Airtel), and bank transfers.",
                "security": "All payments are processed through Stripe's PCI-compliant, encrypted payment gateway.",
                "refund": "Refunds are processed within 5-10 business days after return approval.",
                "invoice": "Invoices are sent to your email and available in your order history.",
                "failed": "If your payment failed, please check your card details and try again. If the issue persists, contact your bank.",
            },
            "shipping": {
                "cost": "Shipping costs are calculated based on order total, weight, and delivery location. Orders over $50 qualify for free standard shipping.",
                "delivery": "Standard shipping: 3-5 business days. Express shipping: 1-2 business days.",
                "tracking": "Tracking information is sent via WhatsApp once your order ships.",
                "international": "International shipping is available to 50+ countries. Duties and taxes may apply.",
                "delayed": "Shipping delays can occur due to weather, customs, or carrier issues. We'll keep you updated on your order status.",
            },
            "products": {
                "warranty": "Most products come with a 1-year manufacturer warranty.",
                "quality": "All products are quality-checked before shipping.",
                "sizing": "Please refer to the size guide on the product page for accurate sizing information.",
                "availability": "Product availability is updated in real-time. Out-of-stock items can be backordered.",
                "authenticity": "All products are 100% authentic and sourced directly from manufacturers.",
            },
            "account": {
                "reset": "To reset your password, go to the login page and click 'Forgot Password'.",
                "update": "You can update your profile information through our web dashboard.",
                "delete": "To delete your account, contact our support team with your account details.",
            },
        }

    def _build_faq(self) -> Dict[str, List[Dict]]:
        faq: Dict[str, List[Dict]] = {}
        for section, items in self.kb.items():
            faq[section] = [{"question": k.replace("_", " ").capitalize(), "answer": v} for k, v in items.items()]
        return faq

    # ------------------------------------------------------------------
    # Intent detection
    # ------------------------------------------------------------------
    INTENT_PATTERNS: Dict[str, List[str]] = {
        "order_tracking": ["track", "where is my order", "order status", "delivery status", "shipping status"],
        "order_return": ["return", "refund", "exchange", "replacement", "send back"],
        "order_cancel": ["cancel", "stop order", "change order", "modify order"],
        "payment": ["pay", "payment", "card", "mobile money", "transfer", "charge", "billing", "m-pesa"],
        "shipping": ["shipping", "delivery", "cost", "international", "ship"],
        "product": ["product", "item", "quality", "warranty", "sizing", "size", "authentic"],
        "account": ["account", "password", "profile", "login", "forgot", "sign up", "register"],
        "complaint": ["complaint", "issue", "problem", "not working", "broken", "defective", "bad", "worst"],
        "feedback": ["feedback", "review", "rating", "suggestion", "improve", "love", "great"],
        "greeting": ["hello", "hi", "hey", "good morning", "good evening", "good afternoon"],
        "thanks": ["thank", "thanks", "appreciate", "grateful"],
    }

    def detect_intent(self, message: str) -> str:
        msg = message.lower().strip()
        for intent, patterns in self.INTENT_PATTERNS.items():
            for p in patterns:
                if p in msg:
                    return intent
        return "general"

    # ------------------------------------------------------------------
    # Sentiment analysis
    # ------------------------------------------------------------------
    POSITIVE_WORDS = {"good", "great", "excellent", "happy", "love", "thank", "amazing", "awesome", "perfect", "best", "wonderful", "fantastic", "satisfied", "please"}
    NEGATIVE_WORDS = {"bad", "terrible", "horrible", "angry", "upset", "disappointed", "frustrated", "worse", "worst", "hate", "annoying", "broken", "defective", "unacceptable", "poor"}

    def analyze_sentiment(self, message: str) -> Dict[str, Any]:
        words = set(re.findall(r"[a-z]+", message.lower()))
        pos = len(words & self.POSITIVE_WORDS)
        neg = len(words & self.NEGATIVE_WORDS)
        score = pos - neg * 2
        if score > 0:
            label = "positive"
        elif score < 0:
            label = "negative"
        else:
            label = "neutral"
        return {"label": label, "score": score, "positive_signals": pos, "negative_signals": neg}

    # ------------------------------------------------------------------
    # Response generation
    # ------------------------------------------------------------------
    def process(self, message: str, customer_id: str = None, context: Dict = None) -> Dict[str, Any]:
        intent = self.detect_intent(message)
        sentiment = self.analyze_sentiment(message)
        response = self._generate_response(message, intent, sentiment, context)
        ticket = None

        if self._should_create_ticket(intent, sentiment):
            ticket = self._create_ticket(customer_id, message, intent, sentiment)

        return {
            "response": response,
            "intent": intent,
            "sentiment": sentiment,
            "ticket": ticket,
        }

    def _generate_response(self, message: str, intent: str, sentiment: Dict, context: Dict = None) -> str:
        # Try FAQ match first
        faq_match = self._faq_match(message)
        if faq_match:
            return faq_match

        responses = {
            "order_tracking": self._get_kb("orders", "tracking"),
            "order_return": self._get_kb("orders", "return"),
            "order_cancel": self._get_kb("orders", "cancel"),
            "payment": self._get_kb("payments", "methods"),
            "shipping": self._get_kb("shipping", "delivery"),
            "product": self._get_kb("products", "warranty"),
            "account": self._get_kb("account", "reset"),
            "complaint": "I understand your frustration. Let me create a support ticket for you. A representative will contact you within 24 hours to resolve this.",
            "feedback": "Thank you for your feedback! We value your input and use it to improve our products and services.",
            "greeting": "Hello! Welcome to our store. I can help you with product info, orders, payments, shipping, and support. What can I help you with?",
            "thanks": "You're welcome! Is there anything else I can help you with?",
        }

        if sentiment["label"] == "negative" and intent not in ("complaint",):
            return "I'm sorry to hear that. Let me help resolve this. " + responses.get(intent, "Could you provide more details so I can assist you better?")

        return responses.get(intent, "I'm here to help! You can ask about products, orders, payments, shipping, or account issues. What would you like to know?")

    def _faq_match(self, message: str) -> Optional[str]:
        msg_words = set(message.lower().split())
        best_match = None
        best_overlap = 0.0
        for _section, articles in self.faq.items():
            for article in articles:
                q_words = set(article["question"].lower().split())
                if not q_words:
                    continue
                overlap = len(msg_words & q_words) / len(q_words)
                if overlap > best_overlap and overlap > 0.45:
                    best_overlap = overlap
                    best_match = article["answer"]
        return best_match

    def _get_kb(self, category: str, topic: str) -> str:
        return self.kb.get(category, {}).get(topic, "Let me connect you with a human agent for more detailed assistance.")

    # ------------------------------------------------------------------
    # Ticketing
    # ------------------------------------------------------------------
    def _should_create_ticket(self, intent: str, sentiment: Dict) -> bool:
        return intent in ("complaint", "order_return", "order_cancel") or sentiment["label"] == "negative"

    def _create_ticket(self, customer_id: str, message: str, intent: str, sentiment: Dict) -> Dict:
        tid = f"TKT-{int(time.time())}-{uuid.uuid4().hex[:6].upper()}"
        ticket = {
            "id": tid,
            "customer_id": customer_id,
            "status": "open",
            "priority": "high" if sentiment["label"] == "negative" else "medium",
            "category": intent,
            "description": message,
            "sentiment": sentiment["label"],
            "created_at": datetime.utcnow().isoformat(),
            "messages": [{"role": "user", "content": message, "ts": datetime.utcnow().isoformat()}],
        }
        self.tickets[tid] = ticket
        logger.info("Created ticket %s (intent=%s, sentiment=%s)", tid, intent, sentiment["label"])
        return ticket

    def add_ticket_message(self, ticket_id: str, role: str, content: str) -> bool:
        if ticket_id not in self.tickets:
            return False
        self.tickets[ticket_id]["messages"].append({"role": role, "content": content, "ts": datetime.utcnow().isoformat()})
        self.tickets[ticket_id]["updated_at"] = datetime.utcnow().isoformat()
        return True

    def resolve_ticket(self, ticket_id: str, resolution: str) -> bool:
        if ticket_id not in self.tickets:
            return False
        self.tickets[ticket_id]["status"] = "resolved"
        self.tickets[ticket_id]["resolution"] = resolution
        self.tickets[ticket_id]["resolved_at"] = datetime.utcnow().isoformat()
        return True

    def list_tickets(self, status: str = None) -> List[Dict]:
        tickets = list(self.tickets.values())
        if status:
            tickets = [t for t in tickets if t["status"] == status]
        return sorted(tickets, key=lambda t: t["created_at"], reverse=True)
