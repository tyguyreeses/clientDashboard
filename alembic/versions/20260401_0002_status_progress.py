"""Track forward entry times for wedding workflow statuses."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260401_0002"
down_revision = "20260401_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wedding_status_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("wedding_id", sa.Integer(), sa.ForeignKey("weddings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.Integer(), nullable=False),
        sa.Column("forward_entered_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN (0, 1, 2, 3, 4, 5, 6)", name="ck_wedding_status_progress_status_valid"),
        sa.UniqueConstraint("wedding_id", "status", name="uq_wedding_status_progress_status"),
    )
    op.create_index("ix_wedding_status_progress_wedding_id", "wedding_status_progress", ["wedding_id"])
    op.execute(
        sa.text(
            "INSERT INTO wedding_status_progress (wedding_id, status, forward_entered_at) "
            "SELECT id, status, updated_at FROM weddings"
        )
    )


def downgrade() -> None:
    op.drop_index("ix_wedding_status_progress_wedding_id", table_name="wedding_status_progress")
    op.drop_table("wedding_status_progress")
