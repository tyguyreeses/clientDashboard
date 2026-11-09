from __future__ import annotations

from fastapi.routing import APIRoute

from client_dashboard.api.admin import router


BUSINESS_OPERATIONS = {
    ("POST", "/api/admin/clients"),
    ("GET", "/api/admin/clients"),
    ("GET", "/api/admin/clients/{client_id}"),
    ("PATCH", "/api/admin/clients/{client_id}"),
    ("DELETE", "/api/admin/clients/{client_id}"),
    ("POST", "/api/admin/weddings"),
    ("GET", "/api/admin/weddings"),
    ("GET", "/api/admin/weddings/{wedding_id}"),
    ("PATCH", "/api/admin/weddings/{wedding_id}"),
    ("DELETE", "/api/admin/weddings/{wedding_id}"),
    ("POST", "/api/admin/weddings/{wedding_id}/party-members"),
    ("GET", "/api/admin/weddings/{wedding_id}/party-members"),
    ("GET", "/api/admin/party-members/{party_member_id}"),
    ("PATCH", "/api/admin/party-members/{party_member_id}"),
    ("DELETE", "/api/admin/party-members/{party_member_id}"),
    ("POST", "/api/admin/pricing-versions/save-preview"),
    ("POST", "/api/admin/pricing-versions/save"),
    ("GET", "/api/admin/pricing-versions"),
    ("GET", "/api/admin/pricing-versions/{pricing_version_id}"),
    ("DELETE", "/api/admin/pricing-versions/{pricing_version_id}"),
    ("GET", "/api/admin/invoices"),
    ("GET", "/api/admin/invoices/{invoice_id}"),
    ("POST", "/api/admin/weddings/{wedding_id}/invoice"),
    ("GET", "/api/admin/weddings/{wedding_id}/invoice"),
    ("GET", "/api/admin/invoices/{invoice_id}/assistant-receipt"),
    ("POST", "/api/admin/payments"),
    ("GET", "/api/admin/payments/{payment_id}"),
    ("PATCH", "/api/admin/payments/{payment_id}"),
    ("DELETE", "/api/admin/payments/{payment_id}"),
    ("GET", "/api/admin/weddings/{wedding_id}/payments"),
}


def application_operations() -> set[tuple[str, str]]:
    return {
        (method, route.path)
        for route in router.routes
        if isinstance(route, APIRoute)
        for method in route.methods
        if method in {"GET", "POST", "PATCH", "PUT", "DELETE"}
    }


def test_business_api_inventory_is_exactly_the_authenticated_admin_surface():
    operations = application_operations()
    actual = {(method, path) for method, path in operations if path.startswith("/api/admin/")}
    assert actual == BUSINESS_OPERATIONS

    old_paths = {path.removeprefix("/api/admin") for _, path in BUSINESS_OPERATIONS}
    assert not any(path in old_paths for _, path in operations)


def test_anonymous_requests_cannot_access_any_business_operation(anonymous_client):
    client = anonymous_client
    for method, path in BUSINESS_OPERATIONS:
        response = client.request(method, path.replace("{client_id}", "1").replace("{wedding_id}", "1").replace("{party_member_id}", "1").replace("{pricing_version_id}", "1").replace("{invoice_id}", "1").replace("{payment_id}", "1"))
        assert response.status_code == 401, (method, path, response.status_code, response.text)
