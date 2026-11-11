from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select

from client_dashboard import models  # noqa: F401
from ..database import engine
from ..settings import get_database_url, get_sqlite_path


EXPECTED_TABLES = (
    "clients",
    "weddings",
    "wedding_party_members",
    "wedding_status_progress",
    "pricing_versions",
    "invoices",
    "assistant_receipts",
    "payments",
    "users",
    "sessions",
    "oauth_attempts",
    "rate_limit_buckets",
    "audit_events",
    "auth_state",
    "inquiry_attempts",
)


def _expected_columns() -> dict[str, set[str]]:
    return {
        table.name: {column.name for column in table.columns}
        for table in models.Base.metadata.sorted_tables
    }


def _expected_indexes() -> set[str]:
    return {
        index.name
        for table in models.Base.metadata.sorted_tables
        for index in table.indexes
        if index.name is not None
    }


def _seed_default_pricing() -> None:
    with engine.begin() as connection:
        if connection.exec_driver_sql("SELECT 1 FROM pricing_versions LIMIT 1").first():
            return
        connection.exec_driver_sql(
            """INSERT INTO pricing_versions
            (name, name_normalized, revision, bride_price, trial_price, bridesmaid_price, flowergirl_price,
             early_morning_fee, assistant_fee, assistant_cut, assistant_bridesmaid_cut,
             base_travel_fee, travel_fee, deposit_percentage, travel_discount_percentage,
             bride_duration_minutes, bridesmaid_updo_duration_minutes,
             bridesmaid_down_duration_minutes, flowergirl_duration_minutes,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
            ("Default pricing", "default pricing", 1, 120, 120, 90, 45, 40, 40, 50, 75, 25, 0.75, 50, 20, 75, 30, 45, 30),
        )


def main() -> None:
    # Existing data may be discarded. Resetting guarantees that legacy
    # location and invoice-version columns are not carried into this schema.
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    models.Base.metadata.drop_all(bind=engine)
    alembic_config = Config(str(Path(__file__).resolve().parents[3] / "alembic.ini"))
    command.upgrade(alembic_config, "head")
    _seed_default_pricing()

    with engine.connect() as connection:
        connection.execute(select(1))

    inspector = inspect(engine)
    existing_tables = tuple(
        table for table in inspector.get_table_names() if table != "alembic_version"
    )
    missing_tables = sorted(set(EXPECTED_TABLES) - set(existing_tables))
    unexpected_tables = sorted(set(existing_tables) - set(EXPECTED_TABLES))
    assert not missing_tables, f"Missing tables: {missing_tables}"
    assert not unexpected_tables, f"Unexpected tables: {unexpected_tables}"

    actual_columns = {
        table: {column["name"] for column in inspector.get_columns(table)}
        for table in EXPECTED_TABLES
    }
    missing_columns = {
        table: sorted(columns - actual_columns[table])
        for table, columns in _expected_columns().items()
        if columns - actual_columns[table]
    }
    assert not missing_columns, f"Missing columns: {missing_columns}"

    actual_indexes = {
        index["name"]
        for table in EXPECTED_TABLES
        for index in inspector.get_indexes(table)
        if index["name"] is not None
    }
    missing_indexes = sorted(_expected_indexes() - actual_indexes)
    assert not missing_indexes, f"Missing indexes: {missing_indexes}"

    print(f"Connected successfully using {get_database_url()}")
    if engine.dialect.name == "sqlite" and not os.getenv("DATABASE_URL"):
        print(f"SQLite file: {get_sqlite_path()}")
    print(f"Verified tables: {', '.join(EXPECTED_TABLES)}")
    print("Verified single current invoice per wedding")


if __name__ == "__main__":
    main()
