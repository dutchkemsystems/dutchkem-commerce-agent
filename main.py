#!/usr/bin/env python3
"""Main entry point for the WhatsApp AI Commerce Agent.

Usage:
    python main.py                  # Start admin API + WhatsApp bridge
    python main.py --api-only       # Start admin API only
    python main.py --seed           # Seed sample products
    python main.py --status         # Print system status
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("commerce.main")


def build_config() -> dict:
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


def seed_products(orch):
    """Seed sample products into the database."""
    from commerce.models import Product

    sample_products = [
        {"name": "Premium Wireless Headphones", "description": "Noise-cancelling Bluetooth headphones with 30hr battery", "price": 79.99, "category": "Electronics", "subcategory": "Audio", "brand": "SoundMax", "sku": "ELEC-WH-001", "stock_quantity": 150, "rating": 4.5, "reviews_count": 234, "images": ["https://example.com/headphones.jpg"], "tags": ["wireless", "bluetooth", "noise-cancelling"]},
        {"name": "Organic Cotton T-Shirt", "description": "Soft organic cotton t-shirt, available in multiple colors", "price": 24.99, "category": "Clothing", "subcategory": "T-Shirts", "brand": "EcoWear", "sku": "CLTH-TS-001", "stock_quantity": 300, "rating": 4.2, "reviews_count": 89, "images": ["https://example.com/tshirt.jpg"], "tags": ["organic", "cotton", "sustainable"]},
        {"name": "Stainless Steel Water Bottle", "description": "750ml insulated water bottle, keeps drinks cold 24hrs", "price": 18.50, "category": "Home & Kitchen", "subcategory": "Drinkware", "brand": "HydroLife", "sku": "HOME-WB-001", "stock_quantity": 500, "rating": 4.7, "reviews_count": 456, "images": ["https://example.com/bottle.jpg"], "tags": ["insulated", "eco-friendly", "reusable"]},
        {"name": "Laptop Stand - Aluminum", "description": "Adjustable aluminum laptop stand for ergonomic workspace", "price": 39.99, "category": "Electronics", "subcategory": "Accessories", "brand": "DeskPro", "sku": "ELEC-LS-001", "stock_quantity": 75, "rating": 4.4, "reviews_count": 167, "images": ["https://example.com/stand.jpg"], "tags": ["ergonomic", "aluminum", "adjustable"]},
        {"name": "Yoga Mat - Non-Slip", "description": "6mm thick non-slip yoga mat with carrying strap", "price": 29.99, "category": "Sports", "subcategory": "Yoga", "brand": "FlexFit", "sku": "SPRT-YM-001", "stock_quantity": 200, "rating": 4.6, "reviews_count": 312, "images": ["https://example.com/yogamat.jpg"], "tags": ["yoga", "non-slip", "fitness"]},
        {"name": "LED Desk Lamp", "description": "Dimmable LED desk lamp with USB charging port", "price": 34.99, "category": "Home & Kitchen", "subcategory": "Lighting", "brand": "BrightSpace", "sku": "HOME-DL-001", "stock_quantity": 120, "rating": 4.3, "reviews_count": 98, "images": ["https://example.com/lamp.jpg"], "tags": ["LED", "dimmable", "USB"]},
        {"name": "Running Shoes - Pro", "description": "Lightweight running shoes with cushioned sole", "price": 89.99, "category": "Sports", "subcategory": "Footwear", "brand": "SpeedStep", "sku": "SPRT-RS-001", "stock_quantity": 80, "rating": 4.8, "reviews_count": 521, "images": ["https://example.com/shoes.jpg"], "tags": ["running", "lightweight", "cushioned"]},
        {"name": "Portable Charger 20000mAh", "description": "High-capacity portable charger with fast charging", "price": 44.99, "category": "Electronics", "subcategory": "Power", "brand": "PowerUp", "sku": "ELEC-PC-001", "stock_quantity": 180, "rating": 4.5, "reviews_count": 289, "images": ["https://example.com/charger.jpg"], "tags": ["portable", "fast-charge", "20000mah"]},
        {"name": "Ceramic Coffee Mug Set (4)", "description": "Set of 4 handcrafted ceramic mugs, 350ml each", "price": 32.00, "category": "Home & Kitchen", "subcategory": "Drinkware", "brand": "CraftHome", "sku": "HOME-CM-004", "stock_quantity": 90, "rating": 4.4, "reviews_count": 145, "images": ["https://example.com/mugs.jpg"], "tags": ["ceramic", "handcrafted", "set"]},
        {"name": "Bluetooth Speaker - Mini", "description": "Compact waterproof Bluetooth speaker with 12hr battery", "price": 29.99, "category": "Electronics", "subcategory": "Audio", "brand": "SoundMax", "sku": "ELEC-BS-001", "stock_quantity": 220, "rating": 4.3, "reviews_count": 198, "images": ["https://example.com/speaker.jpg"], "tags": ["bluetooth", "waterproof", "portable"]},
    ]

    session = orch.db.get_session()
    try:
        existing = session.query(Product).count()
        if existing > 0:
            logger.info("Database already has %d products, skipping seed.", existing)
            return

        for pdata in sample_products:
            p = Product(**pdata)
            session.add(p)
        session.commit()
        logger.info("Seeded %d sample products.", len(sample_products))
    finally:
        session.close()


def run_server(orch, api_only: bool = False):
    """Run the Flask admin API and optionally the WhatsApp bridge."""
    from commerce.admin_api import create_app

    app = create_app(orch)

    if not api_only:
        logger.info("Starting WhatsApp bridge...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(orch.start_whatsapp())

    port = int(os.getenv("COMMERCE_PORT", "8080"))
    logger.info("Starting Admin API on port %d...", port)
    app.run(host="0.0.0.0", port=port, debug=False)


def print_status(orch):
    """Print system status."""
    import json
    status = orch.get_status()
    print(json.dumps(status, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(description="WhatsApp AI Commerce Agent")
    parser.add_argument("--api-only", action="store_true", help="Start API without WhatsApp bridge")
    parser.add_argument("--seed", action="store_true", help="Seed sample products")
    parser.add_argument("--status", action="store_true", help="Print system status")
    args = parser.parse_args()

    config = build_config()

    from commerce.orchestrator import CommerceOrchestrator
    orch = CommerceOrchestrator(config)

    if args.seed:
        seed_products(orch)
        return

    if args.status:
        print_status(orch)
        return

    run_server(orch, api_only=args.api_only)


if __name__ == "__main__":
    main()
