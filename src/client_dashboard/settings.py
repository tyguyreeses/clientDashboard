from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_PATH = BASE_DIR / "data" / "client_dashboard.db"


def _resolve_sqlite_path(raw_path: str | None) -> Path:
    path = Path(raw_path) if raw_path else DEFAULT_SQLITE_PATH
    if not path.is_absolute():
        path = BASE_DIR / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    sqlite_path = _resolve_sqlite_path(os.getenv("SQLITE_DB_PATH"))
    return f"sqlite+pysqlite:///{sqlite_path.as_posix()}"


def get_sqlite_path() -> Path:
    return _resolve_sqlite_path(os.getenv("SQLITE_DB_PATH"))

