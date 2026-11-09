"""Seed the initial pricing policy on a fresh database."""
from alembic import op
import sqlalchemy as sa

revision = "20260401_0008"
down_revision = "20260401_0007"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    exists = bind.execute(sa.text("SELECT 1 FROM pricing_versions LIMIT 1")).first()
    if exists:
        return

    bind.execute(
        sa.text(
            """INSERT INTO pricing_versions
            (name, name_normalized, revision, bride_price, trial_price, bridesmaid_price, flowergirl_price,
             early_morning_fee, assistant_fee, assistant_cut, assistant_bridesmaid_cut,
             base_travel_fee, travel_fee, deposit_percentage, travel_discount_percentage,
             bride_duration_minutes, bridesmaid_updo_duration_minutes,
             bridesmaid_down_duration_minutes, flowergirl_duration_minutes,
             created_at, updated_at)
            VALUES
            (:name, :name_normalized, :revision, :bride_price, :trial_price, :bridesmaid_price,
             :flowergirl_price, :early_morning_fee, :assistant_fee, :assistant_cut,
             :assistant_bridesmaid_cut, :base_travel_fee, :travel_fee, :deposit_percentage,
             :travel_discount_percentage, :bride_duration_minutes,
             :bridesmaid_updo_duration_minutes, :bridesmaid_down_duration_minutes,
             :flowergirl_duration_minutes, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"""
        ),
        {
            "name": "Default pricing",
            "name_normalized": "default pricing",
            "revision": 1,
            "bride_price": 120,
            "trial_price": 120,
            "bridesmaid_price": 90,
            "flowergirl_price": 45,
            "early_morning_fee": 40,
            "assistant_fee": 40,
            "assistant_cut": 50,
            "assistant_bridesmaid_cut": 75,
            "base_travel_fee": 25,
            "travel_fee": 0.75,
            "deposit_percentage": 50,
            "travel_discount_percentage": 20,
            "bride_duration_minutes": 75,
            "bridesmaid_updo_duration_minutes": 30,
            "bridesmaid_down_duration_minutes": 45,
            "flowergirl_duration_minutes": 30,
        },
    )


def downgrade():
    # Do not remove pricing data during a migration rollback.
    pass
