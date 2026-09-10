from __future__ import annotations

from sqlalchemy import select

from client_dashboard.database import engine
from client_dashboard.settings import get_database_url, get_sqlite_path


def main() -> None:
    with engine.connect() as connection:
        connection.execute(select(1))

    print(f"Connected successfully using {get_database_url()}")
    print(f"SQLite file: {get_sqlite_path()}")


if __name__ == "__main__":
    main()

