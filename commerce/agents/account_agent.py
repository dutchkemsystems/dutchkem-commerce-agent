"""Account Agent — customer profile management."""

from __future__ import annotations

from typing import Any, Dict


class AccountAgent:
    """Handles customer account queries and profile management."""

    def __init__(self, ecommerce_engine):
        self.ecommerce = ecommerce_engine

    def process(self, message: str, customer_id: str = None, context: Dict = None) -> Dict[str, Any]:
        msg = message.lower().strip()

        if any(kw in msg for kw in ["profile", "my info", "my details", "account info"]):
            return self._get_profile(customer_id)

        if any(kw in msg for kw in ["update", "change name", "change email", "edit profile"]):
            return self._update_profile(message, customer_id)

        if any(kw in msg for kw in ["loyalty", "points", "rewards"]):
            return self._loyalty_info(customer_id)

        if any(kw in msg for kw in ["order count", "total spent", "my stats"]):
            return self._customer_stats(customer_id)

        return {"response": "I can help with your account. Try:\n- 'my profile'\n- 'update my name to [name]'\n- 'loyalty points'\n- 'my stats'", "action": "help"}

    def _get_profile(self, customer_id: str) -> Dict[str, Any]:
        if not customer_id:
            return {"response": "Please provide your phone number to access your account.", "action": "need_phone"}
        profile = self.ecommerce.get_or_create_customer(customer_id)
        return {
            "response": (
                f"Your Profile:\n"
                f"Name: {profile.get('first_name', 'N/A')} {profile.get('last_name', '')}\n"
                f"Phone: {profile.get('phone', 'N/A')}\n"
                f"Email: {profile.get('email', 'N/A')}\n"
                f"Total Orders: {profile.get('order_count', 0)}\n"
                f"Total Spent: ${profile.get('total_spent', 0):.2f}\n"
                f"Loyalty Points: {profile.get('loyalty_points', 0)}"
            ),
            "action": "profile",
            "profile": profile,
        }

    def _update_profile(self, message: str, customer_id: str) -> Dict[str, Any]:
        import re
        updates = {}
        name_match = re.search(r"name to (.+)", message, re.I)
        email_match = re.search(r"email to (.+)", message, re.I)

        if name_match:
            parts = name_match.group(1).strip().split()
            updates["first_name"] = parts[0] if parts else None
            updates["last_name"] = " ".join(parts[1:]) if len(parts) > 1 else None
        if email_match:
            updates["email"] = email_match.group(1).strip()

        if not updates:
            return {"response": "Please specify what to update (e.g., 'update my name to John Doe').", "action": "no_updates"}

        # In production, update the database
        return {"response": f"Profile updated: {', '.join(updates.keys())}.", "action": "updated", "updates": updates}

    def _loyalty_info(self, customer_id: str) -> Dict[str, Any]:
        profile = self.ecommerce.get_or_create_customer(customer_id)
        points = profile.get("loyalty_points", 0)
        return {
            "response": (
                f"Loyalty Program:\n"
                f"Your Points: {points}\n"
                f"Points Value: ${points * 0.01:.2f}\n\n"
                f"Earn 1 point per $1 spent. Redeem at checkout."
            ),
            "action": "loyalty",
        }

    def _customer_stats(self, customer_id: str) -> Dict[str, Any]:
        profile = self.ecommerce.get_or_create_customer(customer_id)
        return {
            "response": (
                f"Your Stats:\n"
                f"Total Orders: {profile.get('order_count', 0)}\n"
                f"Total Spent: ${profile.get('total_spent', 0):.2f}\n"
                f"Loyalty Points: {profile.get('loyalty_points', 0)}\n"
                f"Member Since: {profile.get('created_at', 'N/A')[:10] if profile.get('created_at') else 'N/A'}"
            ),
            "action": "stats",
        }
