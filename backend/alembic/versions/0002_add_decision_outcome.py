"""Add outcome column to decisions table

Revision ID: 0002_add_decision_outcome
Revises: 0001_initial_schema
Create Date: 2026-08-31 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_add_decision_outcome"
down_revision: Union[str, Sequence[str], None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "decisions",
        sa.Column("outcome", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("decisions", "outcome")
