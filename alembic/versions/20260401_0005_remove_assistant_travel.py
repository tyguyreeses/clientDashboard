"""Remove assistant travel pricing and receipt amounts."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260401_0005"
down_revision = "20260401_0004"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("pricing_versions") as batch_op:
        batch_op.drop_constraint("ck_pricing_assistant_travel_cut_nonnegative", type_="check")
        batch_op.drop_column("assistant_travel_fee_cut")

    with op.batch_alter_table("assistant_receipts") as batch_op:
        batch_op.drop_column("assistant_travel")


def downgrade():
    with op.batch_alter_table("pricing_versions") as batch_op:
        batch_op.add_column(sa.Column("assistant_travel_fee_cut", sa.Numeric(10, 2), nullable=False, server_default="0"))
        batch_op.create_check_constraint(
            "ck_pricing_assistant_travel_cut_nonnegative",
            "assistant_travel_fee_cut >= 0",
        )

    with op.batch_alter_table("assistant_receipts") as batch_op:
        batch_op.add_column(sa.Column("assistant_travel", sa.Numeric(10, 2), nullable=False, server_default="0"))
