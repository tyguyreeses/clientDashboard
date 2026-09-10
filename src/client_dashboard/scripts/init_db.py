from __future__ import annotations

from sqlalchemy import inspect, select

from client_dashboard import models  # noqa: F401
from client_dashboard.database import engine
from client_dashboard.settings import get_database_url, get_sqlite_path


EXPECTED_TABLES = (
    "clients",
    "weddings",
    "wedding_party_members",
    "pricing_versions",
    "invoices",
    "payments",
)
EXPECTED_INVOICE_COLUMNS = ("id", "wedding_id", "version_number", "pricing_version_id")
INVOICE_VERSION_INDEX = "uq_invoices_wedding_id_version_number"


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

        invoice_indexes = {index["name"] for index in inspector.get_indexes("invoices")}
        if INVOICE_VERSION_INDEX not in invoice_indexes:
            connection.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_invoices_wedding_id_version_number "
                "ON invoices (wedding_id, version_number)"
            )


def main() -> None:
    models.Base.metadata.create_all(bind=engine)
    _ensure_invoice_versioning()

    with engine.connect() as connection:
        connection.execute(select(1))

    inspector = inspect(engine)
    existing_tables = tuple(inspector.get_table_names())
    missing_tables = sorted(set(EXPECTED_TABLES) - set(existing_tables))
    unexpected_tables = sorted(set(existing_tables) - set(EXPECTED_TABLES))
    assert not missing_tables, f"Missing tables: {missing_tables}"
    assert not unexpected_tables, f"Unexpected tables: {unexpected_tables}"
    invoice_columns = {column["name"] for column in inspector.get_columns("invoices")}
    missing_invoice_columns = sorted(
        set(EXPECTED_INVOICE_COLUMNS) - set(invoice_columns)
    )
    assert not missing_invoice_columns, f"Missing invoice columns: {missing_invoice_columns}"
    invoice_indexes = {index["name"] for index in inspector.get_indexes("invoices")}
    assert (
        INVOICE_VERSION_INDEX in invoice_indexes
    ), f"Missing invoice index: {INVOICE_VERSION_INDEX}"

    print(f"Connected successfully using {get_database_url()}")
    print(f"SQLite file: {get_sqlite_path()}")
    print(f"Verified tables: {', '.join(EXPECTED_TABLES)}")
    print("Verified invoice versioning: version_number + per-wedding unique index")


if __name__ == "__main__":
    main()
