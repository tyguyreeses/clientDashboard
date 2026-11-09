from __future__ import annotations


def test_public_api_is_limited_to_health_and_authentication(anonymous_client):
    client = anonymous_client
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404


def test_me_rejects_anonymous_requests_without_leaking_authentication_data(anonymous_client):
    client = anonymous_client
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert "csrf" not in response.text.lower()
    assert "token" not in response.text.lower()


def test_public_root_is_a_noninteractive_coming_soon_page(anonymous_client):
    client = anonymous_client
    response = client.get("/")
    assert response.status_code == 200
    document = response.text.lower()
    assert "coming soon" in document
    assert "hair by maddie" in document
    assert "<a " not in document
    assert "<form" not in document
