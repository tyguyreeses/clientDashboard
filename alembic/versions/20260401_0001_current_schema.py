"""Create the current client dashboard schema.

Revision ID: 20260401_0001
Revises:
Create Date: 2026-04-01
"""
from __future__ import annotations

from alembic import op

from client_dashboard import models  # noqa: F401

revision = "20260401_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This is the baseline migration for the project. Future schema changes
    # should be represented by normal Alembic revisions rather than changing
    # the models and recreating the database.
    # Keep later revisions responsible for tables introduced after the baseline.
    tables = [
        table for table in models.Base.metadata.sorted_tables
        if table.name != "wedding_status_progress"
    ]
    models.Base.metadata.create_all(bind=op.get_bind(), tables=tables)


def downgrade() -> None:
    models.Base.metadata.drop_all(bind=op.get_bind())
