"""Database models for the WhatsApp Commerce Agent."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy import JSON, TypeDecorator
import uuid as _uuid_mod


class GUID(TypeDecorator):
    """Platform-independent GUID/UUID type. Stores as string for SQLite, native UUID for Postgres."""
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if isinstance(value, _uuid_mod.UUID):
                return str(value)
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                return _uuid_mod.UUID(value)
            except (ValueError, AttributeError):
                return value
        return value
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------
class Product(Base):
    __tablename__ = "products"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(300), nullable=False, index=True)
    description = Column(Text, default="")
    price = Column(Float, nullable=False)
    compare_at_price = Column(Float, nullable=True)
    category = Column(String(150), nullable=True, index=True)
    subcategory = Column(String(150), nullable=True)
    brand = Column(String(150), nullable=True)
    sku = Column(String(80), unique=True, nullable=False)
    stock_quantity = Column(Integer, default=0)
    in_stock = Column(Boolean, default=True)
    weight = Column(Float, default=1.0)
    images = Column(JSON, default=list)
    attributes = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    rating = Column(Float, default=0.0)
    reviews_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------
class Customer(Base):
    __tablename__ = "customers"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    phone = Column(String(30), unique=True, nullable=False, index=True)
    email = Column(String(250), nullable=True, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    preferences = Column(JSON, default=dict)
    cart = Column(JSON, default=dict)
    wishlist = Column(JSON, default=list)
    order_count = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)
    loyalty_points = Column(Integer, default=0)
    stripe_customer_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    orders = relationship("Order", back_populates="customer")


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------
class Order(Base):
    __tablename__ = "orders"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    order_number = Column(String(30), unique=True, nullable=False, index=True)
    customer_id = Column(GUID(), ForeignKey("customers.id"))
    status = Column(String(50), default="pending", index=True)
    items = Column(JSON, default=list)
    subtotal = Column(Float, nullable=False)
    tax = Column(Float, default=0.0)
    shipping_cost = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    total = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    payment_method = Column(String(50), nullable=True)
    payment_status = Column(String(50), default="pending")
    transaction_id = Column(String(120), nullable=True)
    shipping_address = Column(JSON, default=dict)
    billing_address = Column(JSON, default=dict)
    shipping_tracking = Column(JSON, default=dict)
    notes = Column(JSON, default=dict)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="orders")


# ---------------------------------------------------------------------------
# Support Ticket
# ---------------------------------------------------------------------------
class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    ticket_number = Column(String(30), unique=True, nullable=False, index=True)
    customer_id = Column(GUID(), ForeignKey("customers.id"), nullable=True)
    status = Column(String(50), default="open", index=True)
    priority = Column(String(20), default="medium")
    category = Column(String(100), nullable=True)
    subject = Column(String(300), nullable=True)
    description = Column(Text, nullable=True)
    messages = Column(JSON, default=list)
    assignee = Column(String(100), nullable=True)
    resolution = Column(Text, nullable=True)
    sentiment = Column(String(20), default="neutral")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)


# ---------------------------------------------------------------------------
# Payment Transaction
# ---------------------------------------------------------------------------
class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    order_id = Column(GUID(), ForeignKey("orders.id"), nullable=True)
    customer_id = Column(GUID(), ForeignKey("customers.id"), nullable=True)
    stripe_payment_intent_id = Column(String(120), nullable=True, index=True)
    stripe_charge_id = Column(String(120), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    status = Column(String(50), default="pending")
    payment_method = Column(String(50), nullable=True)
    card_last4 = Column(String(4), nullable=True)
    card_brand = Column(String(20), nullable=True)
    error_message = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Shipment Tracking
# ---------------------------------------------------------------------------
class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    order_id = Column(GUID(), ForeignKey("orders.id"))
    carrier = Column(String(50), nullable=False)
    tracking_number = Column(String(100), nullable=False, index=True)
    service_type = Column(String(100), nullable=True)
    status = Column(String(50), default="pending")
    label_url = Column(Text, nullable=True)
    estimated_delivery = Column(DateTime, nullable=True)
    actual_delivery = Column(DateTime, nullable=True)
    events = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Analytics Event
# ---------------------------------------------------------------------------
class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False, index=True)
    customer_id = Column(GUID(), nullable=True)
    order_id = Column(GUID(), nullable=True)
    data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Knowledge Base Article
# ---------------------------------------------------------------------------
class KBArticle(Base):
    __tablename__ = "kb_articles"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    title = Column(String(300), nullable=False)
    body = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    tags = Column(JSON, default=list)
    upvotes = Column(Integer, default=0)
    downvotes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Engine (thin wrapper)
# ---------------------------------------------------------------------------
class DatabaseEngine:
    """Manages the SQLAlchemy engine, sessions, and table creation."""

    def __init__(self, db_url: str):
        self.engine = create_engine(db_url, pool_pre_ping=True, pool_size=10)
        Base.metadata.create_all(self.engine)
        self.SessionFactory = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.SessionFactory()

    def dispose(self):
        self.engine.dispose()
