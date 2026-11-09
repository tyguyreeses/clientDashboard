# Deployment

Use the Nginx template with real TLS paths and environment values supplied outside Git. Uvicorn listens only on `127.0.0.1`; Nginx is the public endpoint. Set every `TODO_*` value during deployment. Apply Alembic migrations only after taking and verifying a local SQLite backup. Enable the cleanup timer after deployment. Off-host backups are intentionally deferred; follow `PRODUCTION_BACKUP_FUTURE.md` before adding them.
