from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_deployed_root_has_a_noninteractive_static_coming_soon_asset_with_public_links():
    page = ROOT / "frontend" / "public" / "coming-soon" / "index.html"

    assert page.is_file()
    content = page.read_text().lower()
    assert "coming soon" in content
    assert "<form" not in content
    assert "<script" not in content
    assert 'href="/admin"' in content
    assert 'href="/inquiry"' in content


def test_react_coming_soon_exposes_admin_and_inquiry_routes():
    source = (ROOT / "frontend" / "src" / "main.jsx").read_text()

    assert 'href="/admin"' in source
    assert 'href="/inquiry"' in source
    assert 'path === "/inquiry"' in source


def test_nginx_serves_the_spa_for_the_public_inquiry_route():
    config = (ROOT / "deploy" / "nginx" / "client-dashboard.conf.template").read_text()

    assert "location = /inquiry" in config or "location ~ ^/(?:admin|inquiry)" in config
    assert "try_files $uri /index.html" in config


def test_identity_recovery_is_available_only_as_an_operator_cli():
    command = ROOT / "src" / "client_dashboard" / "scripts" / "recover_identity.py"

    assert command.is_file()
    assert "/recover" not in (ROOT / "src" / "client_dashboard" / "api" / "auth.py").read_text()
