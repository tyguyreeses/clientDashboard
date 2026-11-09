from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from client_dashboard.models import AuthState
from client_dashboard.settings import get_settings


class _OAuthResponse:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self.body


class _FakeOAuthClient:
    def __init__(self, client_id, client_secret):
        assert client_id == "google-client"
        assert client_secret == "google-secret"
        self.token = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def request(self, method, url, **kwargs):
        assert method == "GET"
        assert url.endswith("openid-configuration")
        assert kwargs == {"withhold_token": True}
        return _OAuthResponse({
                "token_endpoint": "https://oauth.example/token",
                "userinfo_endpoint": "https://oauth.example/userinfo",
            })

    async def get(self, url, **kwargs):
        assert url == "https://oauth.example/userinfo"
        assert kwargs == {}
        assert self.token == {"access_token": "access-token"}
        return _OAuthResponse({
            "sub": "google-subject",
            "email": "heymaddie@hairbymaddieee.com",
            "email_verified": True,
            "name": "Maddie",
        })

    async def fetch_token(self, endpoint, **kwargs):
        assert endpoint == "https://oauth.example/token"
        assert kwargs["code"] == "authorization-code"
        assert kwargs["redirect_uri"] == "http://localhost:5173/api/auth/google/callback"
        self.token = {"access_token": "access-token"}
        return self.token


def test_google_callback_creates_a_session_from_verified_userinfo(
    anonymous_client, db_session_factory, monkeypatch
):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "google-client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "google-secret")
    monkeypatch.setenv("GOOGLE_CALLBACK_URL", "http://localhost:5173/api/auth/google/callback")
    monkeypatch.setenv("AUTH_BOOTSTRAP_ENABLED", "true")
    get_settings.cache_clear()
    monkeypatch.setattr("authlib.integrations.httpx_client.AsyncOAuth2Client", _FakeOAuthClient)

    try:
        with db_session_factory() as db:
            db.add(AuthState(id=1))
            db.commit()

        started = anonymous_client.get("/api/auth/google/login", follow_redirects=False)
        state = parse_qs(urlparse(started.headers["location"]).query)["state"][0]
        response = anonymous_client.get(
            f"/api/auth/google/callback?state={state}&code=authorization-code",
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/admin"
        authenticated = anonymous_client.get("/api/auth/me")
        assert authenticated.status_code == 200
        assert authenticated.json()["user"]["email"] == "heymaddie@hairbymaddieee.com"
    finally:
        get_settings.cache_clear()


def test_logout_returns_the_session_cookie_deletion_header(client):
    """The browser must receive the deletion header on the actual 204 response."""
    csrf = client.get("/api/auth/me").json()["csrf_token"]
    response = client.post(
        "/api/auth/logout",
        headers={"Origin": "http://localhost:5173", "X-CSRF-Token": csrf},
    )

    assert response.status_code == 204
    assert "session=\"\"" in response.headers["set-cookie"]
    assert "Max-Age=0" in response.headers["set-cookie"]


def test_failed_oauth_callback_uses_a_clean_server_flash_redirect(anonymous_client):
    """Callback errors must not disclose state through the login URL."""
    started = anonymous_client.get("/api/auth/google/login", follow_redirects=False)
    assert started.status_code == 302

    response = anonymous_client.get("/api/auth/google/callback?state=wrong", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"
    assert "flash" in response.headers["set-cookie"].lower()


def test_flash_is_one_use_and_does_not_expose_callback_details(anonymous_client):
    response = anonymous_client.get("/api/auth/flash")

    assert response.status_code == 200
    assert response.json() in ({}, {"category": None})
    assert "flash" in response.headers["set-cookie"].lower()
