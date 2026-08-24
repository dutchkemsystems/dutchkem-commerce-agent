"""E-commerce Engine — catalog, cart, orders, recommendations."""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from commerce.models import (
    Customer,
    Order,
    Product,
    DatabaseEngine,
)


class EcommerceEngine:
    """Full e-commerce functionality: products, cart, orders, recommendations."""

    def __init__(self, db: DatabaseEngine):
        self.db = db

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _session(self) -> Session:
        return self.db.get_session()

    @staticmethod
    def _product_to_dict(p: Product) -> Dict[str, Any]:
        return {
            "id": str(p.id),
            "name": p.name,
            "description": p.description,
            "price": p.price,
            "compare_at_price": p.compare_at_price,
            "category": p.category,
            "subcategory": p.subcategory,
            "brand": p.brand,
            "sku": p.sku,
            "stock_quantity": p.stock_quantity,
            "in_stock": p.in_stock,
            "weight": p.weight,
            "images": p.images or [],
            "attributes": p.attributes or {},
            "tags": p.tags or [],
            "rating": p.rating,
            "reviews_count": p.reviews_count,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }

    @staticmethod
    def _cart_to_dict(cart: Dict) -> Dict[str, Any]:
        items = cart.get("items", [])
        return {
            "items": items,
            "total": round(sum(i.get("total", 0) for i in items), 2),
            "count": len(items),
        }

    @staticmethod
    def _order_to_dict(o: Order) -> Dict[str, Any]:
        return {
            "id": str(o.id),
            "order_number": o.order_number,
            "customer_id": str(o.customer_id),
            "status": o.status,
            "items": o.items or [],
            "subtotal": o.subtotal,
            "tax": o.tax,
            "shipping_cost": o.shipping_cost,
            "discount": o.discount,
            "total": o.total,
            "currency": o.currency,
            "payment_method": o.payment_method,
            "payment_status": o.payment_status,
            "transaction_id": o.transaction_id,
            "shipping_address": o.shipping_address or {},
            "billing_address": o.billing_address or {},
            "shipping_tracking": o.shipping_tracking or {},
            "notes": o.notes or {},
            "metadata": o.metadata_ or {},
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "updated_at": o.updated_at.isoformat() if o.updated_at else None,
        }

    @staticmethod
    def _generate_order_number() -> str:
        return f"ORD-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8].upper()}"

    # ------------------------------------------------------------------
    # Product CRUD
    # ------------------------------------------------------------------
    def get_product(self, product_id: str) -> Optional[Dict]:
        s = self._session()
        try:
            p = s.query(Product).filter(Product.id == product_id).first()
            return self._product_to_dict(p) if p else None
        finally:
            s.close()

    def get_product_by_sku(self, sku: str) -> Optional[Dict]:
        s = self._session()
        try:
            p = s.query(Product).filter(Product.sku == sku).first()
            return self._product_to_dict(p) if p else None
        finally:
            s.close()

    def search_products(self, query: str, limit: int = 20) -> List[Dict]:
        s = self._session()
        try:
            q = s.query(Product).filter(
                or_(
                    Product.name.ilike(f"%{query}%"),
                    Product.description.ilike(f"%{query}%"),
                    Product.brand.ilike(f"%{query}%"),
                    Product.category.ilike(f"%{query}%"),
                )
            )
            return [self._product_to_dict(p) for p in q.limit(limit).all()]
        finally:
            s.close()

    def get_category_products(
        self, category: str, subcategory: str = None, limit: int = 50
    ) -> List[Dict]:
        s = self._session()
        try:
            q = s.query(Product).filter(Product.category == category)
            if subcategory:
                q = q.filter(Product.subcategory == subcategory)
            return [self._product_to_dict(p) for p in q.limit(limit).all()]
        finally:
            s.close()

    def get_all_categories(self) -> List[str]:
        s = self._session()
        try:
            rows = s.query(Product.category).distinct().all()
            return [r[0] for r in rows if r[0]]
        finally:
            s.close()

    def create_product(self, data: Dict[str, Any]) -> Dict:
        s = self._session()
        try:
            p = Product(**{k: v for k, v in data.items() if hasattr(Product, k)})
            s.add(p)
            s.commit()
            s.refresh(p)
            return self._product_to_dict(p)
        finally:
            s.close()

    def update_product(self, product_id: str, data: Dict[str, Any]) -> Optional[Dict]:
        s = self._session()
        try:
            p = s.query(Product).filter(Product.id == product_id).first()
            if not p:
                return None
            for k, v in data.items():
                if hasattr(Product, k) and k not in ("id", "created_at"):
                    setattr(p, k, v)
            p.updated_at = datetime.utcnow()
            s.commit()
            s.refresh(p)
            return self._product_to_dict(p)
        finally:
            s.close()

    # ------------------------------------------------------------------
    # Customer / Cart
    # ------------------------------------------------------------------
    def get_or_create_customer(self, phone: str, **kwargs) -> Dict:
        s = self._session()
        try:
            c = s.query(Customer).filter(Customer.phone == phone).first()
            if c:
                return {
                    "id": str(c.id),
                    "phone": c.phone,
                    "email": c.email,
                    "first_name": c.first_name,
                    "last_name": c.last_name,
                    "order_count": c.order_count,
                    "total_spent": c.total_spent,
                    "loyalty_points": c.loyalty_points,
                    "cart": c.cart or {},
                }
            c = Customer(phone=phone, **kwargs)
            s.add(c)
            s.commit()
            s.refresh(c)
            return {
                "id": str(c.id),
                "phone": c.phone,
                "email": c.email,
                "first_name": c.first_name,
                "last_name": c.last_name,
                "order_count": 0,
                "total_spent": 0.0,
                "loyalty_points": 0,
                "cart": {},
            }
        finally:
            s.close()

    def get_cart(self, customer_id: str) -> Dict:
        s = self._session()
        try:
            c = s.query(Customer).filter(Customer.id == customer_id).first()
            return self._cart_to_dict(c.cart or {}) if c else {"items": [], "total": 0, "count": 0}
        finally:
            s.close()

    def add_to_cart(
        self, customer_id: str, product_id: str, quantity: int = 1
    ) -> Dict:
        s = self._session()
        try:
            c = s.query(Customer).filter(Customer.id == customer_id).first()
            if not c:
                raise ValueError("Customer not found")
            p = s.query(Product).filter(Product.id == product_id).first()
            if not p:
                raise ValueError("Product not found")
            if p.stock_quantity < quantity:
                raise ValueError("Insufficient stock")

            cart = c.cart or {"items": []}
            items = cart.get("items", [])

            found = False
            for item in items:
                if item.get("product_id") == str(p.id):
                    item["quantity"] += quantity
                    item["total"] = round(item["price"] * item["quantity"], 2)
                    found = True
                    break

            if not found:
                items.append(
                    {
                        "product_id": str(p.id),
                        "name": p.name,
                        "price": p.price,
                        "quantity": quantity,
                        "total": round(p.price * quantity, 2),
                        "sku": p.sku,
                        "image": (p.images or [None])[0],
                    }
                )

            cart["items"] = items
            c.cart = cart
            s.commit()
            return self._cart_to_dict(cart)
        finally:
            s.close()

    def remove_from_cart(self, customer_id: str, product_id: str) -> Dict:
        s = self._session()
        try:
            c = s.query(Customer).filter(Customer.id == customer_id).first()
            if not c:
                raise ValueError("Customer not found")
            cart = c.cart or {"items": []}
            cart["items"] = [
                i for i in cart.get("items", []) if i.get("product_id") != product_id
            ]
            c.cart = cart
            s.commit()
            return self._cart_to_dict(cart)
        finally:
            s.close()

    def clear_cart(self, customer_id: str) -> Dict:
        s = self._session()
        try:
            c = s.query(Customer).filter(Customer.id == customer_id).first()
            if c:
                c.cart = {"items": []}
                s.commit()
            return {"items": [], "total": 0, "count": 0}
        finally:
            s.close()

    # ------------------------------------------------------------------
    # Wishlist
    # ------------------------------------------------------------------
    def add_to_wishlist(self, customer_id: str, product_id: str) -> List[str]:
        s = self._session()
        try:
            c = s.query(Customer).filter(Customer.id == customer_id).first()
            if not c:
                raise ValueError("Customer not found")
            wl = c.wishlist or []
            if product_id not in wl:
                wl.append(product_id)
            c.wishlist = wl
            s.commit()
            return wl
        finally:
            s.close()

    def remove_from_wishlist(self, customer_id: str, product_id: str) -> List[str]:
        s = self._session()
        try:
            c = s.query(Customer).filter(Customer.id == customer_id).first()
            if not c:
                raise ValueError("Customer not found")
            wl = [pid for pid in (c.wishlist or []) if pid != product_id]
            c.wishlist = wl
            s.commit()
            return wl
        finally:
            s.close()

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------
    def create_order(self, customer_id: str) -> Dict:
        s = self._session()
        try:
            c = s.query(Customer).filter(Customer.id == customer_id).first()
            if not c:
                raise ValueError("Customer not found")
            cart = c.cart or {"items": []}
            if not cart.get("items"):
                raise ValueError("Cart is empty")

            order = Order()
            order.order_number = self._generate_order_number()
            order.customer_id = c.id
            order.items = cart["items"]
            order.subtotal = round(sum(i["total"] for i in cart["items"]), 2)
            order.shipping_cost = self._calc_shipping(cart["items"])
            order.tax = round(order.subtotal * 0.05, 2)
            order.total = round(order.subtotal + order.shipping_cost + order.tax, 2)
            order.status = "pending"
            order.payment_status = "pending"
            s.add(order)

            c.cart = {"items": []}
            c.order_count = (c.order_count or 0) + 1
            c.total_spent = (c.total_spent or 0) + order.total
            s.commit()
            s.refresh(order)

            # reduce stock
            for item in order.items:
                prod = s.query(Product).filter(Product.id == item.get("product_id")).first()
                if prod:
                    prod.stock_quantity = max(0, prod.stock_quantity - item.get("quantity", 0))
                    prod.in_stock = prod.stock_quantity > 0
            s.commit()

            return self._order_to_dict(order)
        finally:
            s.close()

    def get_order(self, order_id: str) -> Optional[Dict]:
        s = self._session()
        try:
            o = s.query(Order).filter(Order.id == order_id).first()
            return self._order_to_dict(o) if o else None
        finally:
            s.close()

    def get_order_by_number(self, order_number: str) -> Optional[Dict]:
        s = self._session()
        try:
            o = s.query(Order).filter(Order.order_number == order_number).first()
            return self._order_to_dict(o) if o else None
        finally:
            s.close()

    def get_customer_orders(
        self, customer_id: str, limit: int = 50
    ) -> List[Dict]:
        s = self._session()
        try:
            orders = (
                s.query(Order)
                .filter(Order.customer_id == customer_id)
                .order_by(Order.created_at.desc())
                .limit(limit)
                .all()
            )
            return [self._order_to_dict(o) for o in orders]
        finally:
            s.close()

    def update_order_status(self, order_id: str, status: str) -> Dict:
        valid = {"pending", "paid", "processing", "shipped", "delivered", "cancelled", "refunded"}
        if status not in valid:
            raise ValueError(f"Invalid status: {status}")
        s = self._session()
        try:
            o = s.query(Order).filter(Order.id == order_id).first()
            if not o:
                raise ValueError("Order not found")
            o.status = status
            o.updated_at = datetime.utcnow()
            s.commit()
            return self._order_to_dict(o)
        finally:
            s.close()

    def add_tracking_info(
        self, order_id: str, carrier: str, tracking_number: str
    ) -> Dict:
        s = self._session()
        try:
            o = s.query(Order).filter(Order.id == order_id).first()
            if not o:
                raise ValueError("Order not found")
            o.shipping_tracking = {
                "carrier": carrier,
                "tracking_number": tracking_number,
                "status": "shipped",
                "updated_at": datetime.utcnow().isoformat(),
            }
            o.status = "shipped"
            o.updated_at = datetime.utcnow()
            s.commit()
            return self._order_to_dict(o)
        finally:
            s.close()

    # ------------------------------------------------------------------
    # Recommendations (simple popularity-based)
    # ------------------------------------------------------------------
    def get_recommendations(self, customer_id: str = None, limit: int = 10) -> List[Dict]:
        s = self._session()
        try:
            purchased_ids: set = set()
            if customer_id:
                orders = s.query(Order).filter(Order.customer_id == customer_id).all()
                for o in orders:
                    for item in o.items or []:
                        purchased_ids.add(item.get("product_id"))

            q = s.query(Product).filter(Product.in_stock == True)
            if purchased_ids:
                q = q.filter(~Product.id.in_(purchased_ids))
            return [self._product_to_dict(p) for p in q.order_by(Product.rating.desc()).limit(limit).all()]
        finally:
            s.close()

    # ------------------------------------------------------------------
    # Stock helpers
    # ------------------------------------------------------------------
    def check_stock(self, product_id: str) -> Dict:
        s = self._session()
        try:
            p = s.query(Product).filter(Product.id == product_id).first()
            if not p:
                return {"product_id": product_id, "available": False, "quantity": 0}
            return {
                "product_id": str(p.id),
                "available": p.in_stock and p.stock_quantity > 0,
                "quantity": p.stock_quantity,
                "sku": p.sku,
            }
        finally:
            s.close()

    def adjust_stock(self, product_id: str, delta: int) -> Dict:
        s = self._session()
        try:
            p = s.query(Product).filter(Product.id == product_id).first()
            if not p:
                raise ValueError("Product not found")
            p.stock_quantity = max(0, p.stock_quantity + delta)
            p.in_stock = p.stock_quantity > 0
            p.updated_at = datetime.utcnow()
            s.commit()
            return {"product_id": str(p.id), "new_quantity": p.stock_quantity, "in_stock": p.in_stock}
        finally:
            s.close()

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------
    @staticmethod
    def _calc_shipping(items: list) -> float:
        total = sum(i.get("quantity", 1) for i in items) * 5.0
        return min(total, 20.0)
