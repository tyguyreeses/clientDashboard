"""Add pricing correction policy and invoice revision tracking."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260401_0004"
down_revision = "20260401_0003"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, name FROM pricing_versions ORDER BY id")).fetchall()
    normalized: dict[str, int] = {}
    cleaned: list[tuple[int, str, str]] = []
    for pricing_id, raw_name in rows:
        name = raw_name.strip()
        key = name.casefold()
        if not name or len(name) > 15:
            raise RuntimeError(f"Pricing name {raw_name!r} must be 1-15 characters after trimming")
        if key in normalized:
            raise RuntimeError("Normalized pricing name collision; rename conflicting pricing versions before upgrading")
        normalized[key] = pricing_id
        cleaned.append((pricing_id, name, key))

    with op.batch_alter_table("pricing_versions") as batch:
        batch.add_column(sa.Column("name_normalized", sa.String(100), nullable=True))
        batch.add_column(sa.Column("revision", sa.Integer(), nullable=False, server_default="1"))
    for pricing_id, name, key in cleaned:
        bind.execute(
            sa.text("UPDATE pricing_versions SET name=:name, name_normalized=:key WHERE id=:id"),
            {"name": name, "key": key, "id": pricing_id},
        )
    with op.batch_alter_table("pricing_versions") as batch:
        batch.drop_index("ix_pricing_versions_name")
        batch.drop_constraint("ck_pricing_assistant_cut_percent", type_="check")
        batch.alter_column("name", existing_type=sa.String(100), type_=sa.String(15), nullable=False)
        batch.alter_column("name_normalized", existing_type=sa.String(100), type_=sa.String(100), nullable=False)
        batch.alter_column("assistant_bridesmaid_cut", existing_type=sa.Numeric(5, 2), type_=sa.Numeric(10, 2), nullable=False)
        batch.create_check_constraint("ck_pricing_name_nonblank", "length(trim(name)) > 0")
        batch.create_check_constraint("ck_pricing_name_max_length", "length(name) <= 15")
        batch.create_check_constraint("ck_pricing_assistant_cut_nonnegative", "assistant_bridesmaid_cut >= 0")
        batch.create_index("ix_pricing_versions_name_normalized", ["name_normalized"], unique=True)

    with op.batch_alter_table("invoices") as batch:
        batch.add_column(sa.Column("pricing_revision_applied", sa.Integer(), nullable=False, server_default="1"))


def downgrade():
    with op.batch_alter_table("invoices") as batch:
        batch.drop_column("pricing_revision_applied")
    with op.batch_alter_table("pricing_versions") as batch:
        batch.drop_index("ix_pricing_versions_name_normalized")
        batch.drop_constraint("ck_pricing_name_nonblank", type_="check")
        batch.drop_constraint("ck_pricing_name_max_length", type_="check")
        batch.drop_constraint("ck_pricing_assistant_cut_nonnegative", type_="check")
        batch.alter_column("assistant_bridesmaid_cut", existing_type=sa.Numeric(10, 2), type_=sa.Numeric(5, 2), nullable=False)
        batch.alter_column("name", existing_type=sa.String(15), type_=sa.String(100), nullable=False)
        batch.create_check_constraint("ck_pricing_assistant_cut_percent", "assistant_bridesmaid_cut BETWEEN 0 AND 100")
        batch.create_index("ix_pricing_versions_name", ["name"], unique=True)
        batch.drop_column("revision")
        batch.drop_column("name_normalized")
