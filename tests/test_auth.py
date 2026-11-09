from __future__ import annotations


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
