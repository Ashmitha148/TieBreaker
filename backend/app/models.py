from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Float, Boolean, func
from sqlalchemy.orm import relationship

from .database import Base


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    razorpay_order_id = Column(String(100), unique=True, index=True, nullable=False)
    amount = Column(Integer, nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    status = Column(String(50), default="created", nullable=False)
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
    amount = Column(Integer, nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    status = Column(String(50), nullable=False)
    method = Column(String(50), nullable=True)
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
    status = Column(String(50), default="received", nullable=False)
    payload = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)


class Decision(Base):
    __tablename__ = "decisions"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    transaction_id = Column(String(100), index=True, nullable=False)
    fraud_prob = Column(Float, nullable=False)
    fp_prob = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    ltv = Column(Float, nullable=False)
    merchant_category = Column(String(50), nullable=True, index=True)
    recommended_action = Column(String(20), nullable=False)
    baseline_action = Column(String(20), nullable=False)
    savings_vs_baseline = Column(Float, nullable=False)
    model_version = Column(String(64), default="1.0", nullable=False)
    config_version = Column(String(20), default="1.0", nullable=False)
    is_counterintuitive = Column(Boolean, default=False)
    feature_snapshot = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Override(Base):
    __tablename__ = "overrides"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    decision_id = Column(Integer, ForeignKey("decisions.id"), nullable=False)
    transaction_id = Column(String(100), index=True, nullable=False)
    original_action = Column(String(20), nullable=False)
    overridden_action = Column(String(20), nullable=False)
    reason = Column(Text, nullable=False)
    analyst_id = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ConfigHistory(Base):
    __tablename__ = "config_history"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    config_snapshot = Column(Text, nullable=False)
    version = Column(String(20), nullable=False)
    changed_by = Column(String(50), default="system", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    model_version = Column(String(64), nullable=True)
    config_version = Column(String(20), nullable=True)