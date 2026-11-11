"""Persist public inquiry rate-limit attempts."""
from alembic import op
import sqlalchemy as sa

revision = "20260401_0009"
down_revision = "20260401_0008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "inquiry_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ip_address", sa.String(length=45), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_inquiry_attempts_ip_attempted_at",
        "inquiry_attempts",
        ["ip_address", "attempted_at"],
    )


def downgrade():
    op.drop_index("ix_inquiry_attempts_ip_attempted_at", table_name="inquiry_attempts")
    op.drop_table("inquiry_attempts")
