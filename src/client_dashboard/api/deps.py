from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from client_dashboard.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

