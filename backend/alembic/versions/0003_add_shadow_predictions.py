"""add shadow_predictions table (monitoring-only shadow model comparisons)

Revision ID: 0003_add_shadow_predictions
Revises: 0002_add_decision_outcome
Create Date: 2026-09-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: Union[str, Sequence[str]] = "0003_add_shadow_predictions"
down_revision: Union[str, Sequence[str]] = "0002_add_decision_outcome"
branch_labels: Union[str, Sequence[str]] = None
depends_on: Union[str, Sequence[str]] = None


def upgrade() -> None:
    op.create_table(
        "shadow_predictions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("transaction_id", sa.String(100), nullable=True, index=True),
        sa.Column("primary_score", sa.Float, nullable=False),
        sa.Column("shadow_score", sa.Float, nullable=True),
        sa.Column("delta", sa.Float, nullable=True),
        sa.Column("recommended_action", sa.String(20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_shadow_predictions_transaction_id",
        "shadow_predictions",
        ["transaction_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_shadow_predictions_transaction_id", table_name="shadow_predictions")
    op.drop_table("shadow_predictions")