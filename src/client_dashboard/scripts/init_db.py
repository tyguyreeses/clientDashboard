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
INVOICE_SENT_AT_COLUMN = "invoice_sent_at"
WEDDING_HAIR_SERVICE_COUNT_COLUMN = "hair_service_count"
CLIENT_INQUIRY_COLUMNS = {
    "planning_stage": "VARCHAR(30)",
    "makeup_interest": "BOOLEAN",
    "recommendations_if_unavailable": "BOOLEAN",
    "referral_name": "VARCHAR(255)",
    "hair_service_details": "TEXT",
    "archived": "BOOLEAN NOT NULL DEFAULT 0",
}


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


def _ensure_wedding_status_values() -> None:
    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as connection:
        sql = connection.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'weddings'"
        ).scalar() or ""
        if "status IN (0, 1, 2, 3, 4, 5, 6)" in sql and "'complete'" in sql:
            return
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.exec_driver_sql("ALTER TABLE weddings RENAME TO weddings_old")
        connection.exec_driver_sql("""CREATE TABLE weddings (
            id INTEGER NOT NULL PRIMARY KEY,
            client_id INTEGER NOT NULL REFERENCES clients (id),
            wedding_date DATE NOT NULL,
            location VARCHAR(255),
            miles_one_way NUMERIC(8, 2),
            ready_by TIME,
            status INTEGER NOT NULL DEFAULT 1,
            invoice_sent_at DATETIME,
            bridal_trial_status VARCHAR(20) NOT NULL DEFAULT 'not_interested',
            assistant BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            CONSTRAINT ck_weddings_status_valid CHECK (status IN (0, 1, 2, 3, 4, 5, 6)),
            CONSTRAINT ck_weddings_miles_nonnegative CHECK (miles_one_way IS NULL OR miles_one_way >= 0),
            CONSTRAINT ck_weddings_bridal_trial_status_valid CHECK (bridal_trial_status IN ('not_interested', 'interested', 'link_sent', 'booked', 'complete', 'cancelled'))
        )""")
        connection.exec_driver_sql("""INSERT INTO weddings
            (id, client_id, wedding_date, location, miles_one_way, ready_by, status,
             invoice_sent_at, bridal_trial_status, assistant, created_at, updated_at)
            SELECT id, client_id, wedding_date, location, miles_one_way, ready_by, status,
             invoice_sent_at, bridal_trial_status, assistant, created_at, updated_at
            FROM weddings_old""")
        connection.exec_driver_sql("DROP TABLE weddings_old")
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_weddings_client_id ON weddings (client_id)")
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_weddings_wedding_date ON weddings (wedding_date)")
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_weddings_status ON weddings (status)")
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")


def _ensure_party_member_roles() -> None:
    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as connection:
        constraints = connection.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE type = 'table' "
            "AND name = 'wedding_party_members'"
        ).scalar()
        if not constraints or "'M'" in constraints:
            return
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.exec_driver_sql("ALTER TABLE wedding_party_members RENAME TO wedding_party_members_old")
        connection.exec_driver_sql(
            """CREATE TABLE wedding_party_members (
                id INTEGER NOT NULL PRIMARY KEY,
                wedding_id INTEGER NOT NULL REFERENCES weddings (id),
                role VARCHAR(1) NOT NULL,
                hairstyle VARCHAR(1) NOT NULL,
                by_me_quantity SMALLINT NOT NULL DEFAULT 0,
                by_assistant_quantity SMALLINT NOT NULL DEFAULT 0,
                CONSTRAINT ck_wedding_party_members_role_valid CHECK (role IN ('B', 'P', 'J', 'F', 'M', 'O')),
                CONSTRAINT ck_wedding_party_members_hairstyle_valid CHECK (hairstyle IN ('U', 'D')),
                CONSTRAINT ck_wedding_party_members_by_me_nonnegative CHECK (by_me_quantity >= 0),
                CONSTRAINT ck_wedding_party_members_by_assistant_nonnegative CHECK (by_assistant_quantity >= 0)
            )"""
        )
        connection.exec_driver_sql(
            "INSERT INTO wedding_party_members "
            "SELECT id, wedding_id, role, hairstyle, by_me_quantity, by_assistant_quantity "
            "FROM wedding_party_members_old"
        )
        connection.exec_driver_sql("DROP TABLE wedding_party_members_old")
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_wedding_party_members_wedding_id "
            "ON wedding_party_members (wedding_id)"
        )
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")


def _ensure_individual_party_members() -> None:
    with engine.begin() as connection:
        columns = {column["name"] for column in inspect(connection).get_columns("wedding_party_members")}
        if "assistant" in columns:
            return
        rows = connection.exec_driver_sql(
            "SELECT id, wedding_id, role, hairstyle, by_me_quantity, by_assistant_quantity "
            "FROM wedding_party_members"
        ).fetchall()
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.exec_driver_sql("ALTER TABLE wedding_party_members RENAME TO wedding_party_members_old")
        connection.exec_driver_sql(
            """CREATE TABLE wedding_party_members (
                id INTEGER NOT NULL PRIMARY KEY,
                wedding_id INTEGER NOT NULL REFERENCES weddings (id),
                role VARCHAR(1) NOT NULL,
                hairstyle VARCHAR(1) NOT NULL,
                assistant BOOLEAN NOT NULL DEFAULT 0,
                CONSTRAINT ck_wedding_party_members_role_valid CHECK (role IN ('B', 'P', 'J', 'F', 'M', 'O')),
                CONSTRAINT ck_wedding_party_members_hairstyle_valid CHECK (hairstyle IN ('U', 'D')),
                CONSTRAINT ck_wedding_party_members_assistant_valid CHECK (assistant IN (0, 1))
            )"""
        )
        for row_id, wedding_id, role, hairstyle, by_me, by_assistant in rows:
            for assistant, quantity in ((False, by_me), (True, by_assistant)):
                for _ in range(quantity):
                    connection.exec_driver_sql(
                        "INSERT INTO wedding_party_members "
                        "(wedding_id, role, hairstyle, assistant) VALUES (?, ?, ?, ?)",
                        (wedding_id, role, hairstyle, assistant),
                    )
        connection.exec_driver_sql("DROP TABLE wedding_party_members_old")
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_wedding_party_members_wedding_id "
            "ON wedding_party_members (wedding_id)"
        )
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")


def _ensure_hair_service_count() -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        columns = {column["name"] for column in inspector.get_columns("weddings")}
        if WEDDING_HAIR_SERVICE_COUNT_COLUMN not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE weddings ADD COLUMN hair_service_count INTEGER"
            )


def _ensure_invoice_sent_at() -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        columns = {column["name"] for column in inspector.get_columns("weddings")}
        if INVOICE_SENT_AT_COLUMN not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE weddings ADD COLUMN invoice_sent_at DATETIME"
            )


def _ensure_client_inquiry_fields() -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        columns = {column["name"] for column in inspector.get_columns("clients")}
        for name, definition in CLIENT_INQUIRY_COLUMNS.items():
            if name not in columns:
                connection.exec_driver_sql(f"ALTER TABLE clients ADD COLUMN {name} {definition}")


def main() -> None:
    # Migrate the legacy invoice table before create_all attempts to create
    # the current unique index, which depends on version_number.
    if "invoices" in inspect(engine).get_table_names():
        _ensure_invoice_versioning()
    if "weddings" in inspect(engine).get_table_names():
        _ensure_bridal_trial_status()
        _ensure_wedding_status_values()
    if "clients" in inspect(engine).get_table_names():
        _ensure_client_inquiry_fields()
    if "weddings" in inspect(engine).get_table_names():
        _ensure_party_member_roles()
        _ensure_hair_service_count()
        _ensure_invoice_sent_at()
    models.Base.metadata.create_all(bind=engine)
    _ensure_invoice_versioning()
    _ensure_bridal_trial_status()
    _ensure_wedding_status_values()
    _ensure_client_inquiry_fields()
    _ensure_party_member_roles()
    _ensure_individual_party_members()
    _ensure_hair_service_count()
    _ensure_invoice_sent_at()

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
