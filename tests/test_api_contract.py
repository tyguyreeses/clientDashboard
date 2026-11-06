from __future__ import annotations


def test_api_exposes_the_resources_used_by_the_dashboard(client):
    paths = client.get("/openapi.json").json()["paths"]

    expected = {
        ("/clients", "get"),
        ("/clients", "post"),
        ("/clients/{client_id}", "patch"),
        ("/clients/{client_id}", "delete"),
        ("/weddings", "get"),
        ("/weddings", "post"),
        ("/weddings/{wedding_id}", "get"),
        ("/weddings/{wedding_id}", "patch"),
        ("/weddings/{wedding_id}/party-members", "get"),
        ("/payments", "post"),
        ("/weddings/{wedding_id}/payments", "get"),
        ("/weddings/{wedding_id}/invoice", "get"),
        ("/pricing-versions", "get"),
        ("/pricing-versions/save-preview", "post"),
        ("/pricing-versions/save", "post"),
        ("/pricing-versions/{pricing_version_id}", "delete"),
    }

    assert expected <= {
        (path, method)
        for path, operations in paths.items()
        for method in operations
        if method in {"get", "post", "patch", "delete"}
    }


def test_core_resource_responses_have_stable_shapes(client):
    client_data = client.post("/clients", json={"name": "Contract client"}).json()
    assert {"id", "name", "created_at", "updated_at"} <= client_data.keys()

    wedding_data = client.post(
        "/weddings",
        json={
            "client_id": client_data["id"],
            "wedding_date": "2026-10-10",
            "address": "123 Main Street",
        },
    ).json()
    assert {"id", "client_id", "wedding_date", "status", "client", "party_members"} <= wedding_data.keys()
    assert wedding_data["client"]["id"] == client_data["id"]
    assert isinstance(wedding_data["party_members"], list)

    wedding_list = client.get("/weddings").json()
    assert wedding_list
    assert {"id", "client_id", "wedding_date", "status", "client"} <= wedding_list[0].keys()


def test_pricing_and_invoice_contracts_expose_policy_metadata(client):
    schema = client.get("/openapi.json").json()["components"]["schemas"]
    assert {"confirmed", "confirmation_fingerprint"} <= set(schema["PricingSave"]["properties"])
    assert schema["PricingSave"]["properties"]["confirmed"]["const"] is True
    assert {"action", "affected_records", "confirmation_fingerprint", "preview_date"} <= set(schema["PricingPreviewRead"]["properties"])
    assert {"deleted_id", "new_default"} <= set(schema["PricingDeleteRead"]["properties"])
    assert {"revision", "is_default", "created_date", "correction_deadline", "can_delete"} <= set(schema["PricingVersionRead"]["properties"])
    assert {"pricing_revision_applied", "pricing_stale"} <= set(schema["InvoiceRead"]["properties"])


def test_api_uses_expected_http_errors_for_invalid_requests(client):
    assert client.get("/clients/999999").status_code == 404
    assert client.post("/clients", json={}).status_code == 422
    assert client.post(
        "/weddings",
        json={
            "client_id": 999999,
            "wedding_date": "2026-10-10",
            "address": "123 Main Street",
        },
    ).status_code == 404
