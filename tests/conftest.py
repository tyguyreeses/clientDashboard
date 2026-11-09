from __future__ import annotations

from collections.abc import Generator
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from client_dashboard.api.deps import get_db
from client_dashboard.auth.service import create_session, now
from client_dashboard.database import Base
from client_dashboard.main import app
from client_dashboard.models import User


@pytest.fixture()
def db_session_factory(tmp_path: Path):
    db_path = tmp_path / "test_client_dashboard.db"
    engine = create_engine(f"sqlite+pysqlite:///{db_path}", connect_args={"check_same_thread": False})
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    yield factory
    engine.dispose()


def override_database(factory):
    def override_get_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()
    return override_get_db


@pytest.fixture()
def anonymous_client(db_session_factory) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = override_database(db_session_factory)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def client(anonymous_client, db_session_factory):
    with db_session_factory() as db:
        user = User(google_subject="test-subject", email="heymaddie@hairbymaddieee.com", display_name="Test Admin")
        db.add(user); db.flush()
        token, csrf, _ = create_session(db, user)
        db.commit()
    anonymous_client.cookies.set("session", token)
    original_request = anonymous_client.request
    def request(method, url, *args, **kwargs):
        if isinstance(url, str) and url.startswith("/") and not url.startswith("/api") and url != "/":
            url = "/api/admin" + url
        if method.upper() in {"POST", "PUT", "PATCH", "DELETE"} and str(url).startswith("/api/admin"):
            headers = dict(kwargs.pop("headers", {}) or {})
            headers.setdefault("Origin", "http://localhost:5173")
            headers.setdefault("X-CSRF-Token", csrf)
            kwargs["headers"] = headers
        return original_request(method, url, *args, **kwargs)
    anonymous_client.request = request
    return anonymous_client
