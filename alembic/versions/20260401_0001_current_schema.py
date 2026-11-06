"""Create the immutable revision-0001 business schema."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260401_0001"
down_revision = None
branch_labels = None
depends_on = None


def timestamps():
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def upgrade():
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50)), sa.Column("email", sa.String(255)),
        sa.Column("social_media", sa.String(255)), sa.Column("source", sa.String(100)),
        sa.Column("inquiry_date", sa.Date()), sa.Column("notes", sa.Text()),
        sa.Column("planning_stage", sa.String(30)), sa.Column("makeup_interest", sa.Boolean()),
        sa.Column("recommendations_if_unavailable", sa.Boolean()),
        sa.Column("referral_name", sa.String(255)), sa.Column("hair_service_details", sa.Text()),
        sa.Column("is_referral", sa.Boolean(), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False), *timestamps(),
    )
    op.create_index("ix_clients_source", "clients", ["source"])
    op.create_index("ix_clients_inquiry_date", "clients", ["inquiry_date"])
    op.create_table(
        "weddings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("wedding_date", sa.Date(), nullable=False),
        sa.Column("address", sa.String(255), nullable=False), sa.Column("city", sa.String(255)),
        sa.Column("venue", sa.String(255)), sa.Column("miles_one_way", sa.Numeric(8, 2)),
        sa.Column("ready_by", sa.Time()), sa.Column("status", sa.Integer(), nullable=False),
        sa.Column("invoice_sent_at", sa.DateTime(timezone=True)),
        sa.Column("bridal_trial_status", sa.String(20), nullable=False),
        sa.Column("assistant", sa.Boolean(), nullable=False, server_default="0"), *timestamps(),
        sa.CheckConstraint("status IN (0, 1, 2, 3, 4, 5, 6)", name="ck_weddings_status_valid"),
        sa.CheckConstraint("miles_one_way IS NULL OR miles_one_way >= 0", name="ck_weddings_miles_nonnegative"),
        sa.CheckConstraint("bridal_trial_status IN ('not_interested', 'interested', 'link_sent', 'booked', 'complete', 'cancelled')", name="ck_weddings_bridal_trial_status_valid"),
    )
    op.create_index("ix_weddings_client_id", "weddings", ["client_id"])
    op.create_index("ix_weddings_wedding_date", "weddings", ["wedding_date"])
    op.create_index("ix_weddings_status", "weddings", ["status"])
    op.create_table(
        "wedding_party_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("wedding_id", sa.Integer(), sa.ForeignKey("weddings.id"), nullable=False),
        sa.Column("role", sa.String(1), nullable=False), sa.Column("hairstyle", sa.String(1), nullable=False),
        sa.Column("assistant", sa.Boolean(), nullable=False),
        sa.CheckConstraint("role IN ('B', 'P', 'J', 'F', 'M', 'O')", name="ck_wedding_party_members_role_valid"),
        sa.CheckConstraint("hairstyle IN ('U', 'D')", name="ck_wedding_party_members_hairstyle_valid"),
        sa.CheckConstraint("assistant IN (0, 1)", name="ck_wedding_party_members_assistant_valid"),
    )
    op.create_index("ix_wedding_party_members_wedding_id", "wedding_party_members", ["wedding_id"])
    op.create_table(
        "pricing_versions",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(100), nullable=False),
        sa.Column("bride_price", sa.Numeric(10,2), nullable=False), sa.Column("trial_price", sa.Numeric(10,2), nullable=False),
        sa.Column("bridesmaid_price", sa.Numeric(10,2), nullable=False), sa.Column("flowergirl_price", sa.Numeric(10,2), nullable=False),
        sa.Column("early_morning_fee", sa.Numeric(10,2), nullable=False), sa.Column("assistant_fee", sa.Numeric(10,2), nullable=False),
        sa.Column("assistant_bridesmaid_cut", sa.Numeric(5,2), nullable=False), sa.Column("base_travel_fee", sa.Numeric(10,2), nullable=False),
        sa.Column("travel_fee", sa.Numeric(10,2), nullable=False), sa.Column("deposit_percentage", sa.Numeric(5,2), nullable=False),
        sa.Column("travel_discount_percentage", sa.Numeric(5,2), nullable=False),
        sa.Column("bride_duration_minutes", sa.Integer(), nullable=False), sa.Column("bridesmaid_updo_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("bridesmaid_down_duration_minutes", sa.Integer(), nullable=False), sa.Column("flowergirl_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("assistant_travel_fee_cut", sa.Numeric(10,2), nullable=False), *timestamps(),
        sa.CheckConstraint("bride_price >= 0", name="ck_pricing_bride_price_nonnegative"),
        sa.CheckConstraint("trial_price >= 0", name="ck_pricing_trial_price_nonnegative"),
        sa.CheckConstraint("bridesmaid_price >= 0", name="ck_pricing_bridesmaid_price_nonnegative"),
        sa.CheckConstraint("flowergirl_price >= 0", name="ck_pricing_flowergirl_price_nonnegative"),
        sa.CheckConstraint("early_morning_fee >= 0", name="ck_pricing_early_morning_nonnegative"),
        sa.CheckConstraint("assistant_fee >= 0", name="ck_pricing_assistant_fee_nonnegative"),
        sa.CheckConstraint("assistant_bridesmaid_cut BETWEEN 0 AND 100", name="ck_pricing_assistant_cut_percent"),
        sa.CheckConstraint("base_travel_fee >= 0", name="ck_pricing_base_travel_nonnegative"),
        sa.CheckConstraint("travel_fee >= 0", name="ck_pricing_travel_nonnegative"),
        sa.CheckConstraint("deposit_percentage BETWEEN 0 AND 100", name="ck_pricing_deposit_percent"),
        sa.CheckConstraint("travel_discount_percentage BETWEEN 0 AND 100", name="ck_pricing_travel_discount_percent"),
        sa.CheckConstraint("bride_duration_minutes >= 0", name="ck_pricing_bride_duration_nonnegative"),
        sa.CheckConstraint("bridesmaid_updo_duration_minutes >= 0", name="ck_pricing_bridesmaid_updo_duration_nonnegative"),
        sa.CheckConstraint("bridesmaid_down_duration_minutes >= 0", name="ck_pricing_bridesmaid_down_duration_nonnegative"),
        sa.CheckConstraint("flowergirl_duration_minutes >= 0", name="ck_pricing_flowergirl_duration_nonnegative"),
        sa.CheckConstraint("assistant_travel_fee_cut >= 0", name="ck_pricing_assistant_travel_cut_nonnegative"),
    )
    op.create_index("ix_pricing_versions_name", "pricing_versions", ["name"], unique=True)
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("wedding_id", sa.Integer(), sa.ForeignKey("weddings.id"), nullable=False),
        sa.Column("pricing_version_id", sa.Integer(), sa.ForeignKey("pricing_versions.id"), nullable=False),
        *[sa.Column(name, sa.Numeric(10,2), nullable=False) for name in ("services_total", "travel_total", "discount_total", "deposit_amount", "balance_due", "grand_total")],
        sa.Column("calculation_hash", sa.String(64), nullable=False), sa.Column("calculation_snapshot", sa.JSON(), nullable=False),
        sa.Column("line_items", sa.JSON(), nullable=False), sa.Column("timing_details", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False), sa.Column("message_text", sa.Text(), nullable=False), *timestamps(),
        *[sa.CheckConstraint(f"{name} >= 0", name=f"ck_invoices_{label}_nonnegative") for name, label in (("services_total","services"),("travel_total","travel"),("discount_total","discount"),("deposit_amount","deposit"),("balance_due","balance"),("grand_total","grand_total"))],
    )
    op.create_index("ix_invoices_pricing_version_id", "invoices", ["pricing_version_id"])
    op.create_index("uq_invoices_wedding_id", "invoices", ["wedding_id"], unique=True)
    op.create_table(
        "assistant_receipts", sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("assistant_travel", sa.Numeric(10,2), nullable=False), sa.Column("assistant_service_pay", sa.Numeric(10,2), nullable=False),
        sa.Column("assisted_bridesmaid_count", sa.Integer(), nullable=False), sa.Column("assisted_bridesmaid_pay", sa.Numeric(10,2), nullable=False),
        sa.Column("total_paid_to_assistant", sa.Numeric(10,2), nullable=False), sa.Column("business_takehome", sa.Numeric(10,2), nullable=False), *timestamps(),
    )
    op.create_index("ix_assistant_receipts_invoice_id", "assistant_receipts", ["invoice_id"], unique=True)
    op.create_table(
        "payments", sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("wedding_id", sa.Integer(), sa.ForeignKey("weddings.id"), nullable=False),
        sa.Column("amount", sa.Numeric(10,2), nullable=False), sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("payment_method", sa.String(50), nullable=False), sa.Column("notes", sa.Text()), *timestamps(),
        sa.CheckConstraint("amount >= 0", name="ck_payments_amount_nonnegative"),
    )
    op.create_index("ix_payments_wedding_id", "payments", ["wedding_id"])


def downgrade():
    for table in ("payments", "assistant_receipts", "invoices", "pricing_versions", "wedding_party_members", "weddings", "clients"):
        op.drop_table(table)
