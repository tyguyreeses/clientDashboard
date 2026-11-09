from __future__ import annotations

import pytest

from client_dashboard.auth.service import create_session
from client_dashboard.models import User
from client_dashboard.settings import get_settings


def test_csrf_rejects_a_referer_prefix_attack(client):
    """A host suffix is not the approved frontend origin."""
    csrf = client.get("/api/auth/me").json()["csrf_token"]
    response = client.post(
        "/api/auth/logout",
        headers={
            "Origin": "http://localhost:5173",
            "Referer": "http://localhost:5173.evil/logout",
            "X-CSRF-Token": csrf,
        },
    )

    assert response.status_code == 403


def test_production_callback_must_exactly_match_the_approved_callback(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_SECRET", "x" * 32)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "real-client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "real-secret")
    monkeypatch.setenv("GOOGLE_CALLBACK_URL", "https://hairbymaddieee.com.evil/api/auth/google/callback")
    get_settings.cache_clear()

    try:
        with pytest.raises(RuntimeError, match="Invalid authentication configuration"):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_unauthenticated_me_requests_consume_the_me_rate_limit_before_authentication(
    anonymous_client, db_session_factory
):
    """An attacker cannot bypass the auth-route quota by failing authentication."""
    for _ in range(60):
        assert anonymous_client.get("/api/auth/me").status_code == 401

    with db_session_factory() as db:
        user = User(google_subject="subject", email="heymaddie@hairbymaddieee.com")
        db.add(user)
        db.flush()
        token, _, _ = create_session(db, user)
        db.commit()
    anonymous_client.cookies.set("session", token)

    response = anonymous_client.get("/api/auth/me")

    assert response.status_code == 429
    assert int(response.headers["retry-after"]) > 0
