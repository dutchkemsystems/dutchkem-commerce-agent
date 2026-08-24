"""WhatsApp Integration Bridge — bidirectional WhatsApp <-> AI system communication."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class WhatsAppMessage:
    """Represents an incoming WhatsApp message."""

    def __init__(self, sender: str, text: str, message_id: str = None, timestamp: str = None, media: Dict = None):
        self.sender = sender
        self.text = text
        self.message_id = message_id
        self.timestamp = timestamp
        self.media = media

    def to_dict(self) -> Dict:
        return {
            "sender": self.sender,
            "text": self.text,
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "media": self.media,
        }


class WhatsAppBridge:
    """Bridge between WhatsApp and the AI commerce system.

    Supports multiple WhatsApp providers via pluggable backends:
    - whatsapp-web.js (Node.js bridge via subprocess)
    - Meta Cloud API (direct REST)
    - Mock (for development/testing)
    """

    def __init__(self, config: Dict[str, Any], message_handler: Callable = None):
        self.config = config
        self.handler = message_handler
        self.provider = config.get("provider", "mock")
        self.connected = False
        self._client = None

    async def initialize(self) -> bool:
        """Initialize the WhatsApp connection."""
        try:
            if self.provider == "mock":
                logger.info("WhatsApp bridge initialized in MOCK mode")
                self.connected = True
                return True

            if self.provider == "cloud_api":
                return self._init_cloud_api()

            if self.provider == "webjs":
                return await self._init_webjs()

            logger.warning("Unknown WhatsApp provider: %s, using mock", self.provider)
            self.connected = True
            return True

        except Exception as exc:
            logger.error("Failed to initialize WhatsApp bridge: %s", exc)
            return False

    def _init_cloud_api(self) -> bool:
        """Initialize Meta Cloud API."""
        self._client = {
            "type": "cloud_api",
            "phone_number_id": self.config.get("phone_number_id"),
            "access_token": self.config.get("access_token"),
            "verify_token": self.config.get("verify_token"),
            "api_version": self.config.get("api_version", "v18.0"),
        }
        self.connected = True
        logger.info("WhatsApp Cloud API initialized")
        return True

    async def _init_webjs(self) -> bool:
        """Initialize whatsapp-web.js bridge (requires Node.js)."""
        try:
            # In production, this would spawn a Node.js subprocess
            # running whatsapp-web.js and communicate via WebSocket
            logger.info("WhatsApp web.js bridge initialized (placeholder)")
            self.connected = True
            return True
        except Exception as exc:
            logger.error("web.js init failed: %s", exc)
            return False

    async def send_message(self, to: str, text: str, buttons: list = None, list_items: list = None) -> bool:
        """Send a message to a WhatsApp user."""
        if not self.connected:
            logger.warning("Cannot send message: WhatsApp not connected")
            return False

        try:
            if self.provider == "cloud_api":
                return await self._send_cloud_api(to, text, buttons, list_items)
            elif self.provider == "mock":
                logger.info("[MOCK WhatsApp] -> %s: %s", to, text[:100])
                return True
            elif self.provider == "webjs":
                return await self._send_webjs(to, text)

            return False

        except Exception as exc:
            logger.error("Failed to send WhatsApp message: %s", exc)
            return False

    async def _send_cloud_api(self, to: str, text: str, buttons: list = None, list_items: list = None) -> bool:
        """Send via Meta Cloud API."""
        import aiohttp

        url = f"https://graph.facebook.com/{self._client['api_version']}/{self._client['phone_number_id']}/messages"
        headers = {
            "Authorization": f"Bearer {self._client['access_token']}",
            "Content-Type": "application/json",
        }

        # Build message payload
        if buttons and len(buttons) <= 3:
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": text},
                    "action": {"buttons": [{"type": "reply", "reply": {"id": f"btn_{i}", "title": b}} for i, b in enumerate(buttons)]},
                },
            }
        elif list_items:
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "body": {"text": text},
                    "action": {
                        "button": "Options",
                        "sections": [{"title": "Menu", "rows": [{"id": f"row_{i}", "title": item} for i, item in enumerate(list_items)]}],
                    },
                },
            }
        else:
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": text},
            }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    logger.info("Message sent to %s", to)
                    return True
                body = await resp.text()
                logger.error("Cloud API error %s: %s", resp.status, body)
                return False

    async def _send_webjs(self, to: str, text: str) -> bool:
        """Send via whatsapp-web.js bridge."""
        # Placeholder for WebSocket communication with Node.js bridge
        logger.info("[web.js] -> %s: %s", to, text[:100])
        return True

    async def handle_webhook(self, data: Dict) -> Optional[WhatsAppMessage]:
        """Handle incoming webhook from Meta Cloud API."""
        try:
            entry = data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])

            if not messages:
                return None

            msg = messages[0]
            sender = msg.get("from", "")
            text = msg.get("text", {}).get("body", "")
            msg_id = msg.get("id", "")
            ts = msg.get("timestamp", "")

            whatsapp_msg = WhatsAppMessage(sender=sender, text=text, message_id=msg_id, timestamp=ts)

            if self.handler:
                response = await self.handler(whatsapp_msg)
                if response:
                    await self.send_message(sender, response)

            return whatsapp_msg

        except Exception as exc:
            logger.error("Webhook handling error: %s", exc)
            return None

    def disconnect(self):
        """Disconnect from WhatsApp."""
        self.connected = False
        self._client = None
        logger.info("WhatsApp bridge disconnected")
