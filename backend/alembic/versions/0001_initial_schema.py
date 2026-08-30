"""initial schema — create all tables

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-31 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("razorpay_order_id", sa.String(100), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(10), server_default="INR", nullable=False),
        sa.Column("status", sa.String(50), server_default="created", nullable=False),
        sa.Column("receipt", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_orders_id", "orders", ["id"])
    op.create_index("ix_orders_razorpay_order_id", "orders", ["razorpay_order_id"], unique=True)

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("razorpay_payment_id", sa.String(100), nullable=False),
        sa.Column("razorpay_order_id", sa.String(100), nullable=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(10), server_default="INR", nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("method", sa.String(50), nullable=True),
        sa.Column("bank", sa.String(50), nullable=True),
        sa.Column("wallet", sa.String(50), nullable=True),
        sa.Column("vpa", sa.String(100), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("contact", sa.String(50), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_description", sa.Text(), nullable=True),
        sa.Column("error_source", sa.String(100), nullable=True),
        sa.Column("error_step", sa.String(100), nullable=True),
        sa.Column("error_reason", sa.String(100), nullable=True),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_payments_id", "payments", ["id"])
    op.create_index("ix_payments_razorpay_payment_id", "payments", ["razorpay_payment_id"], unique=True)
    op.create_index("ix_payments_razorpay_order_id", "payments", ["razorpay_order_id"])

    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.String(100), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(50), server_default="received", nullable=False),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_webhook_events_id", "webhook_events", ["id"])
    op.create_index("ix_webhook_events_event_id", "webhook_events", ["event_id"], unique=True)
    op.create_index("ix_webhook_events_event_type", "webhook_events", ["event_type"])

    op.create_table(
        "decisions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("transaction_id", sa.String(100), nullable=False),
        sa.Column("fraud_prob", sa.Float(), nullable=False),
        sa.Column("fp_prob", sa.Float(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("ltv", sa.Float(), nullable=False),
        sa.Column("merchant_category", sa.String(50), nullable=True),
        sa.Column("recommended_action", sa.String(20), nullable=False),
        sa.Column("baseline_action", sa.String(20), nullable=False),
        sa.Column("savings_vs_baseline", sa.Float(), nullable=False),
        sa.Column("model_version", sa.String(64), server_default="1.0", nullable=False),
        sa.Column("config_version", sa.String(20), server_default="1.0", nullable=False),
        sa.Column("is_counterintuitive", sa.Boolean(), server_default=sa.false()),
        sa.Column("feature_snapshot", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_decisions_id", "decisions", ["id"])
    op.create_index("ix_decisions_transaction_id", "decisions", ["transaction_id"])
    op.create_index("ix_decisions_merchant_category", "decisions", ["merchant_category"])

    op.create_table(
        "overrides",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("decision_id", sa.Integer(), sa.ForeignKey("decisions.id"), nullable=False),
        sa.Column("transaction_id", sa.String(100), nullable=False),
        sa.Column("original_action", sa.String(20), nullable=False),
        sa.Column("overridden_action", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("analyst_id", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_overrides_id", "overrides", ["id"])
    op.create_index("ix_overrides_transaction_id", "overrides", ["transaction_id"])

    op.create_table(
        "config_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("config_snapshot", sa.Text(), nullable=False),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("changed_by", sa.String(50), server_default="system", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_config_history_id", "config_history", ["id"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user", sa.String(100), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("model_version", sa.String(64), nullable=True),
        sa.Column("config_version", sa.String(20), nullable=True),
    )
    op.create_index("ix_audit_log_id", "audit_log", ["id"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("config_history")
    op.drop_table("overrides")
    op.drop_table("decisions")
    op.drop_table("webhook_events")
    op.drop_table("payments")
    op.drop_table("orders")
