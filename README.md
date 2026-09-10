# Client Dashboard Backend

## Local database setup

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -e .`.
3. Run the database initialization check with `python -m client_dashboard.scripts.init_db`.

## Configuration

- `DATABASE_URL` overrides the database connection string.
- If `DATABASE_URL` is not set, the app uses SQLite with `SQLITE_DB_PATH` or `data/client_dashboard.db`.

## SQLite file location

By default, the local SQLite database is created at `data/client_dashboard.db`.

