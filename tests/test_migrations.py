from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def alembic(db_path: Path, *args: str, check: bool = True):
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path}"
    env["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(ROOT / "src"), env.get("PYTHONPATH")) if value
    )
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=check,
    )


def columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def insert_pricing(connection: sqlite3.Connection, pricing_id: int, name: str) -> None:
    connection.execute(
        """
        INSERT INTO pricing_versions (
            id, name, bride_price, trial_price, bridesmaid_price, flowergirl_price,
            early_morning_fee, assistant_fee, assistant_bridesmaid_cut,
            base_travel_fee, travel_fee, deposit_percentage,
            travel_discount_percentage, bride_duration_minutes,
            bridesmaid_updo_duration_minutes, bridesmaid_down_duration_minutes,
            flowergirl_duration_minutes, assistant_travel_fee_cut, created_at, updated_at
        ) VALUES (?, ?, 120, 110, 90, 45, 40, 150, 75, 25, .75, 50, 20,
                  75, 30, 45, 30, 15, '2026-04-01 12:00:00', '2026-04-01 12:00:00')
        """,
        (pricing_id, name),
    )


def test_fresh_upgrade_has_pricing_policy_schema(tmp_path):
    db_path = tmp_path / "fresh.db"
    alembic(db_path, "upgrade", "head")

    with sqlite3.connect(db_path) as connection:
        assert {"name_normalized", "revision"} <= columns(connection, "pricing_versions")
        assert "pricing_revision_applied" in columns(connection, "invoices")
        assert {"users", "sessions", "oauth_attempts", "rate_limit_buckets", "audit_events", "auth_state"} <= {
            row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        assert revision == "20260401_0007"


def test_populated_0003_upgrade_preserves_invoice_data_and_backfills_revisions(tmp_path):
    db_path = tmp_path / "populated.db"
    alembic(db_path, "upgrade", "20260401_0003")

    snapshot = {"pricing": {"bride_price": "120.00"}, "marker": [1, 2, 3]}
    line_items = [{"description": "Bride", "total": "120.00"}]
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO clients (id, name, is_referral, archived, created_at, updated_at)
            VALUES (1, 'Migration Client', 0, 0, '2026-04-01 12:00:00', '2026-04-01 12:00:00')
            """
        )
        connection.execute(
            """
            INSERT INTO weddings (
                id, client_id, wedding_date, address, status, bridal_trial_status,
                created_at, updated_at
            ) VALUES (
                1, 1, '2026-10-10', '123 Main', 1, 'not_interested',
                '2026-04-01 12:00:00', '2026-04-01 12:00:00'
            )
            """
        )
        insert_pricing(connection, 1, "  Current  ")
        connection.execute(
            """
            INSERT INTO invoices (
                id, wedding_id, pricing_version_id, services_total, travel_total,
                discount_total, deposit_amount, balance_due, grand_total,
                calculation_hash, calculation_snapshot, line_items, timing_details,
                warnings, message_text, created_at, updated_at
            ) VALUES (
                1, 1, 1, 120, 10, 5, 60, 65, 125,
                'known-hash', ?, ?, '{}', '[]', 'Known message',
                '2026-04-01 12:00:00', '2026-04-01 12:00:00'
            )
            """,
            (json.dumps(snapshot), json.dumps(line_items)),
        )
        connection.commit()

    alembic(db_path, "upgrade", "head")

    with sqlite3.connect(db_path) as connection:
        pricing = connection.execute(
            "SELECT name, name_normalized, revision FROM pricing_versions WHERE id = 1"
        ).fetchone()
        assert pricing == ("Current", "current", 1)
        invoice = connection.execute(
            """
            SELECT pricing_version_id, pricing_revision_applied, services_total,
                   travel_total, discount_total, deposit_amount, balance_due,
                   grand_total, calculation_hash, calculation_snapshot, line_items,
                   message_text
            FROM invoices WHERE id = 1
            """
        ).fetchone()
        assert invoice[:9] == (1, 1, 120, 10, 5, 60, 65, 125, "known-hash")
        assert json.loads(invoice[9]) == snapshot
        assert json.loads(invoice[10]) == line_items
        assert invoice[11] == "Known message"


def test_populated_0003_upgrade_rejects_casefold_name_collisions_without_data_loss(tmp_path):
    db_path = tmp_path / "collision.db"
    alembic(db_path, "upgrade", "20260401_0003")
    with sqlite3.connect(db_path) as connection:
        insert_pricing(connection, 1, " Straße ")
        insert_pricing(connection, 2, "STRASSE")
        connection.commit()

    result = alembic(db_path, "upgrade", "head", check=False)
    assert result.returncode != 0
    assert "collision" in (result.stdout + result.stderr).lower()

    with sqlite3.connect(db_path) as connection:
        assert connection.execute(
            "SELECT id, name FROM pricing_versions ORDER BY id"
        ).fetchall() == [(1, " Straße "), (2, "STRASSE")]
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "20260401_0003"


def test_populated_0006_upgrade_preserves_business_records_and_adds_auth_schema(tmp_path):
    db_path = tmp_path / "populated-0006.db"
    alembic(db_path, "upgrade", "20260401_0006")

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO clients (id, name, is_referral, archived, created_at, updated_at)
            VALUES (1, 'Retained Client', 0, 0, '2026-04-01 12:00:00', '2026-04-01 12:00:00')
            """
        )
        connection.commit()

    alembic(db_path, "upgrade", "head")

    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT id, name FROM clients").fetchall() == [(1, "Retained Client")]
        assert {"users", "sessions", "oauth_attempts", "rate_limit_buckets", "audit_events", "auth_state"} <= {
            row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "20260401_0007"
