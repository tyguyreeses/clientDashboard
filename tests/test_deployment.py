from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_deployed_root_has_a_noninteractive_static_coming_soon_asset():
    page = ROOT / "frontend" / "public" / "coming-soon" / "index.html"

    assert page.is_file()
    content = page.read_text().lower()
    assert "coming soon" in content
    assert "<form" not in content
    assert "<script" not in content
    assert "<a " not in content


def test_identity_recovery_is_available_only_as_an_operator_cli():
    command = ROOT / "src" / "client_dashboard" / "scripts" / "recover_identity.py"

    assert command.is_file()
    assert "/recover" not in (ROOT / "src" / "client_dashboard" / "api" / "auth.py").read_text()
