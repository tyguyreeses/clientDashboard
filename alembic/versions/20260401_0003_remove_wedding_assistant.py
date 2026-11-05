"""Remove the redundant wedding-level assistant flag."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260401_0003"
down_revision = "20260401_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "assistant" in {column["name"] for column in inspect(op.get_bind()).get_columns("weddings") }:
        with op.batch_alter_table("weddings") as batch_op:
            batch_op.drop_column("assistant")


def downgrade() -> None:
    with op.batch_alter_table("weddings") as batch_op:
        batch_op.add_column(sa.Column("assistant", sa.Boolean(), nullable=False, server_default="0"))
