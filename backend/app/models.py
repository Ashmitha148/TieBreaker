from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from .database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    razorpay_order_id = Column(String(100), unique=True, index=True, nullable=False)
    amount = Column(Integer, nullable=False)  # Amount in paise (e.g. 50000 for ₹500)
    currency = Column(String(10), default="INR", nullable=False)
    status = Column(String(50), default="created", nullable=False)  # created, attempted, paid, failed
    receipt = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    razorpay_payment_id = Column(String(100), unique=True, index=True, nullable=False)
    razorpay_order_id = Column(String(100), index=True, nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    amount = Column(Integer, nullable=False)  # Amount in paise
    currency = Column(String(10), default="INR", nullable=False)
    status = Column(String(50), nullable=False)  # authorized, captured, failed, refunded
    method = Column(String(50), nullable=True)  # card, upi, netbanking, wallet
    bank = Column(String(50), nullable=True)
    wallet = Column(String(50), nullable=True)
    vpa = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    contact = Column(String(50), nullable=True)
    error_code = Column(String(100), nullable=True)
    error_description = Column(Text, nullable=True)
    error_source = Column(String(100), nullable=True)
    error_step = Column(String(100), nullable=True)
    error_reason = Column(String(100), nullable=True)
    raw_payload = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    order = relationship("Order", back_populates="payments")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id = Column(String(100), unique=True, index=True, nullable=False)
    event_type = Column(String(100), index=True, nullable=False)
    entity_id = Column(String(100), nullable=True)
    status = Column(String(50), default="received", nullable=False)  # received, processed, duplicate, failed
    payload = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)