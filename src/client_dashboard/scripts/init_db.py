from __future__ import annotations

import os

from sqlalchemy import inspect, select

from client_dashboard import models  # noqa: F401
from ..database import engine
from ..settings import get_database_url, get_sqlite_path


EXPECTED_TABLES = (
    "clients",
    "weddings",
    "wedding_party_members",
    "pricing_versions",
    "invoices",
    "payments",
)
INVOICE_VERSION_INDEX = "uq_invoices_wedding_id_version_number"
WEDDING_TRIAL_STATUS_COLUMN = "bridal_trial_status"


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


def _ensure_invoice_versioning() -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        invoice_columns = {
            column["name"] for column in inspector.get_columns("invoices")
        }
        if "version_number" not in invoice_columns:
            connection.exec_driver_sql(
                "ALTER TABLE invoices ADD COLUMN version_number INTEGER NOT NULL DEFAULT 1"
            )

            rows = connection.exec_driver_sql(
                "SELECT id, wedding_id FROM invoices ORDER BY wedding_id, id"
            ).fetchall()
            next_version: dict[int, int] = {}
            for invoice_id, wedding_id in rows:
                version = next_version.get(wedding_id, 1)
                connection.exec_driver_sql(
                    "UPDATE invoices SET version_number = ? WHERE id = ?",
                    (version, invoice_id),
                )
                next_version[wedding_id] = version + 1

        invoice_indexes = {index["name"] for index in inspector.get_indexes("invoices")}
        if INVOICE_VERSION_INDEX not in invoice_indexes:
            connection.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_invoices_wedding_id_version_number "
                "ON invoices (wedding_id, version_number)"
            )


def _ensure_bridal_trial_status() -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        columns = {column["name"] for column in inspector.get_columns("weddings")}
        if WEDDING_TRIAL_STATUS_COLUMN in columns:
            return

        connection.exec_driver_sql(
            "ALTER TABLE weddings ADD COLUMN bridal_trial_status "
            "VARCHAR(20) NOT NULL DEFAULT 'not_interested'"
        )
        if "bridal_trial" in columns:
            connection.exec_driver_sql(
                "UPDATE weddings SET bridal_trial_status = 'interested' "
                "WHERE bridal_trial = 1"
            )


def main() -> None:
    # Migrate the legacy invoice table before create_all attempts to create
    # the current unique index, which depends on version_number.
    if "invoices" in inspect(engine).get_table_names():
        _ensure_invoice_versioning()
    if "weddings" in inspect(engine).get_table_names():
        _ensure_bridal_trial_status()
    models.Base.metadata.create_all(bind=engine)
    _ensure_invoice_versioning()
    _ensure_bridal_trial_status()

    with engine.connect() as connection:
        connection.execute(select(1))

    inspector = inspect(engine)
    existing_tables = tuple(inspector.get_table_names())
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
    print("Verified invoice versioning: version_number + per-wedding unique index")


if __name__ == "__main__":
    main()
