"""Add the assistant payment cut to pricing and receipts."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260401_0006"
down_revision = "20260401_0005"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("pricing_versions") as batch_op:
        batch_op.add_column(
            sa.Column("assistant_cut", sa.Numeric(10, 2), nullable=False, server_default="50.00")
        )
        batch_op.create_check_constraint("ck_pricing_assistant_cut_nonnegative", "assistant_cut >= 0")

    with op.batch_alter_table("assistant_receipts") as batch_op:
        batch_op.alter_column("assistant_service_pay", new_column_name="assistant_cut")


def downgrade():
    with op.batch_alter_table("assistant_receipts") as batch_op:
        batch_op.alter_column("assistant_cut", new_column_name="assistant_service_pay")

    with op.batch_alter_table("pricing_versions") as batch_op:
        batch_op.drop_constraint("ck_pricing_assistant_cut_nonnegative", type_="check")
        batch_op.drop_column("assistant_cut")
