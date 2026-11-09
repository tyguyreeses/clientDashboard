from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    environment: str
    frontend_origin: str
    callback_url: str
    google_client_id: str
    google_client_secret: str
    allowed_email: str
    session_secret: str
    bootstrap_enabled: bool

    @property
    def secure_cookies(self) -> bool:
        return self.environment == "production"


def get_sqlite_path() -> str:
    return os.getenv("SQLITE_DB_PATH", "data/client_dashboard.db")


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", f"sqlite+pysqlite:///{get_sqlite_path()}")


@lru_cache
def get_settings() -> Settings:
    environment = os.getenv("APP_ENV", "test")
    if environment == "production":
        origin = "https://hairbymaddieee.com"
    else:
        origin = "http://localhost:5173"
    settings = Settings(
        environment=environment,
        frontend_origin=os.getenv("FRONTEND_ORIGIN", origin),
        callback_url=os.getenv("GOOGLE_CALLBACK_URL", f"{origin}/api/auth/google/callback"),
        google_client_id=os.getenv("GOOGLE_CLIENT_ID", "test-client-id"),
        google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "test-client-secret"),
        allowed_email=os.getenv("GOOGLE_ALLOWED_EMAIL", "heymaddie@hairbymaddieee.com").strip().casefold(),
        session_secret=os.getenv("SESSION_SECRET", "test-session-secret-at-least-32-bytes"),
        bootstrap_enabled=os.getenv("AUTH_BOOTSTRAP_ENABLED", "false").lower() == "true",
    )
    if environment != "test":
        if len(settings.session_secret.encode()) < 32 or settings.frontend_origin != origin or not settings.callback_url.startswith(origin):
            raise RuntimeError("Invalid authentication configuration")
        if any(value.startswith("test-") or not value for value in (settings.google_client_id, settings.google_client_secret)):
            raise RuntimeError("Google OAuth credentials are required")
    return settings
