from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from client_dashboard.models import Payment, PricingVersion


def test_client_crud(client, db_session_factory):
    create_response = client.post(
        "/clients",
        json={
            "name": "Alyssa Hart",
            "phone": "555-111-2222",
            "email": "alyssa@example.com",
            "source": "instagram",
            "inquiry_date": "2026-09-01",
            "notes": "Initial inquiry",
        },
    )
    assert create_response.status_code == 201
    client_id = create_response.json()["id"]

    get_response = client.get(f"/clients/{client_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Alyssa Hart"

    update_response = client.patch(
        f"/clients/{client_id}",
        json={"notes": "Updated note"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["notes"] == "Updated note"

    list_response = client.get("/clients")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    delete_response = client.delete(f"/clients/{client_id}")
    assert delete_response.status_code == 204

    missing_response = client.get(f"/clients/{client_id}")
    assert missing_response.status_code == 404


def test_wedding_party_payment_and_filters(client, db_session_factory):
    client_id = client.post(
        "/clients",
        json={"name": "Mia Stone", "source": "instagram"},
    ).json()["id"]

    wedding_response = client.post(
        "/weddings",
        json={
            "client_id": client_id,
            "wedding_date": "2026-10-10",
            "address": "123 Main Street",
            "miles_one_way": "24.50",
            "ready_by": "08:30:00",
            "status": 1,
            "bridal_trial_status": "link_sent",
            "assistant": False,
        },
    )
    assert wedding_response.status_code == 201
    wedding_id = wedding_response.json()["id"]

    filtered = client.get("/weddings", params={"source": "instagram"})
    assert filtered.status_code == 200
    assert filtered.json()[0]["id"] == wedding_id

    party_response = client.post(
        f"/weddings/{wedding_id}/party-members",
        json={
            "role": "P",
            "hairstyle": "U",
            "by_me_quantity": 2,
            "by_assistant_quantity": 1,
        },
    )
    assert party_response.status_code == 201
    party_member_id = party_response.json()["id"]

    party_get = client.get(f"/party-members/{party_member_id}")
    assert party_get.status_code == 200
    assert party_get.json()["role"] == "P"

    party_list = client.get(f"/weddings/{wedding_id}/party-members")
    assert party_list.status_code == 200
    assert len(party_list.json()) == 1

    payment_response = client.post(
        "/payments",
        json={
            "wedding_id": wedding_id,
            "amount": "125.00",
            "payment_date": "2026-09-15",
            "payment_method": "cash",
            "notes": "Deposit",
        },
    )
    assert payment_response.status_code == 201
    payment_id = payment_response.json()["id"]

    payment_get = client.get(f"/payments/{payment_id}")
    assert payment_get.status_code == 200
    assert payment_get.json()["amount"] == "125.00"

    with db_session_factory() as session:
        payment = session.get(Payment, payment_id)
        assert payment is not None
        payment.notes = "Updated deposit"
        session.commit()

    update_payment = client.patch(f"/payments/{payment_id}", json={"notes": "Updated deposit"})
    assert update_payment.status_code == 200
    assert update_payment.json()["notes"] == "Updated deposit"

    delete_payment = client.delete(f"/payments/{payment_id}")
    assert delete_payment.status_code == 204

    wedding_detail = client.get(f"/weddings/{wedding_id}")
    assert wedding_detail.status_code == 200
    assert wedding_detail.json()["client"]["id"] == client_id
    assert len(wedding_detail.json()["party_members"]) == 1


def _pricing_payload(name: str, **overrides):
    payload = {
        "name": name,
        "bride_price": "120",
        "trial_price": "120",
        "bridesmaid_price": "90",
        "flowergirl_price": "45",
        "early_morning_fee": "40",
        "assistant_fee": "40",
        "assistant_bridesmaid_cut": "75",
        "base_travel_fee": "25",
        "travel_fee": "0.75",
        "deposit_percentage": "50",
        "travel_discount_percentage": "20",
        "assistant_travel_fee_cut": "15",
        "bride_duration_minutes": 75,
        "bridesmaid_updo_duration_minutes": 30,
        "bridesmaid_down_duration_minutes": 45,
        "flowergirl_duration_minutes": 30,
    }
    payload.update(overrides)
    return payload


def _save_pricing(client, payload):
    preview = client.post("/pricing-versions/save-preview", json=payload)
    assert preview.status_code == 200, preview.text
    response = client.post(
        "/pricing-versions/save",
        json={
            **payload,
            "confirmed": True,
            "confirmation_fingerprint": preview.json()["confirmation_fingerprint"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["version"]


def _invoice_fixture(client, *, pricing_name="Invoice pricing", pricing_overrides=None):
    pricing_payload = _pricing_payload(pricing_name, **(pricing_overrides or {}))
    pricing_id = _save_pricing(client, pricing_payload)["id"]
    client_id = client.post(
        "/clients",
        json={"name": "Invoice Client", "is_referral": True},
    ).json()["id"]
    wedding_id = client.post(
        "/weddings",
        json={
            "client_id": client_id,
            "wedding_date": "2026-10-10",
            "address": "123 Main Street",
            "city": "Salt Lake City",
            "venue": "The Garden Venue",
            "miles_one_way": "10",
            "ready_by": "09:00:00",
            "bridal_trial_status": "booked",
        },
    ).json()["id"]
    client.post(f"/weddings/{wedding_id}/party-members", json={"role": "B", "hairstyle": "U"})
    client.post(
        f"/weddings/{wedding_id}/party-members",
        json={"role": "P", "hairstyle": "U", "assistant": True},
    )
    return pricing_id, client_id, wedding_id


def test_invoice_generation_message_and_assistant_receipt(client):
    pricing_id, _, wedding_id = _invoice_fixture(client)

    generated = client.post(
        f"/weddings/{wedding_id}/invoice",
        json={"pricing_version_id": pricing_id},
    )
    assert generated.status_code == 201
    invoice = generated.json()["invoice"]

    assert invoice["grand_total"] == "329.50"
    assert "Bridal trial: charged separately" in invoice["message_text"]
    assert invoice["warnings"] == []
    assert invoice["timing_details"]["start_time"] == "07:30"
    assert "Invoice Client" in invoice["message_text"]
    assert "123 Main Street" in invoice["message_text"]
    assert "The Garden Venue" in invoice["message_text"]
    assert "bridal trial" in invoice["message_text"].lower()
    assert "business_takehome" not in invoice["message_text"]

    receipt = client.get(f"/invoices/{invoice['id']}/assistant-receipt")
    assert receipt.status_code == 200
    assert receipt.json()["total_paid_to_assistant"] == "107.50"


def test_invoice_overwrites_for_pricing_selection_and_has_no_version(client, db_session_factory):
    first_pricing, _, wedding_id = _invoice_fixture(client)
    with db_session_factory() as session:
        version = session.get(PricingVersion, first_pricing)
        version.created_at = datetime.now(timezone.utc) - timedelta(days=8)
        session.commit()
    second_pricing = _save_pricing(
        client, _pricing_payload("Second pricing", bride_price="200")
    )["id"]

    first = client.post(
        f"/weddings/{wedding_id}/invoice",
        json={"pricing_version_id": first_pricing},
    ).json()["invoice"]
    second = client.post(
        f"/weddings/{wedding_id}/invoice",
        json={"pricing_version_id": second_pricing},
    )
    assert second.status_code == 200
    updated = second.json()["invoice"]

    assert updated["id"] == first["id"]
    assert updated["pricing_version"]["id"] == second_pricing
    assert "version_number" not in updated


def test_invoice_updates_after_invoice_related_edit(client):
    pricing_id, client_id, wedding_id = _invoice_fixture(client)
    generated = client.post(
        f"/weddings/{wedding_id}/invoice",
        json={"pricing_version_id": pricing_id},
    ).json()["invoice"]

    updated_wedding = client.patch(
        f"/weddings/{wedding_id}",
        json={"miles_one_way": "20"},
    )
    assert updated_wedding.status_code == 200

    updated_invoice = client.get(f"/weddings/{wedding_id}/invoice").json()
    assert updated_invoice["id"] == generated["id"]
    assert updated_invoice["travel_total"] != generated["travel_total"]

    updated_client = client.patch(
        f"/clients/{client_id}",
        json={"name": "Updated Invoice Client"},
    )
    assert updated_client.status_code == 200
    assert "Updated Invoice Client" in client.get(
        f"/weddings/{wedding_id}/invoice"
    ).json()["message_text"]


def test_invalid_invoice_update_preserves_existing_invoice(client):
    pricing_id, _, wedding_id = _invoice_fixture(client)
    generated = client.post(
        f"/weddings/{wedding_id}/invoice",
        json={"pricing_version_id": pricing_id},
    ).json()["invoice"]

    edited = client.patch(f"/weddings/{wedding_id}", json={"address": ""})
    assert edited.status_code == 200

    unchanged = client.get(f"/weddings/{wedding_id}/invoice").json()
    assert unchanged["id"] == generated["id"]
    assert unchanged["calculation_hash"] == generated["calculation_hash"]
    assert unchanged["message_text"] == generated["message_text"]


def test_client_edit_returns_invoice_warning_without_changing_invoice(client):
    pricing_id, client_id, wedding_id = _invoice_fixture(client)
    generated = client.post(
        f"/weddings/{wedding_id}/invoice",
        json={"pricing_version_id": pricing_id},
    ).json()["invoice"]

    client.patch(f"/weddings/{wedding_id}", json={"ready_by": None})
    response = client.patch(f"/clients/{client_id}", json={"name": "Warning Client"})

    assert response.status_code == 200
    assert "Missing required fields: ready_by" in response.json()["invoice_warnings"]
    unchanged = client.get(f"/weddings/{wedding_id}/invoice").json()
    assert unchanged["calculation_hash"] == generated["calculation_hash"]


def test_deleting_assistant_member_refreshes_invoice_receipt(client):
    pricing_id, _, wedding_id = _invoice_fixture(client)
    client.post(f"/weddings/{wedding_id}/invoice", json={"pricing_version_id": pricing_id})
    assistant = next(
        member for member in client.get(f"/weddings/{wedding_id}/party-members").json()
        if member["assistant"]
    )

    deleted = client.delete(f"/party-members/{assistant['id']}")

    assert deleted.status_code == 204
    receipt = client.get(
        f"/invoices/{client.get(f'/weddings/{wedding_id}/invoice').json()['id']}/assistant-receipt"
    )
    assert receipt.status_code == 404


def test_invoice_validation_reports_all_missing_required_fields(client):
    client_id = client.post("/clients", json={"name": "Missing Fields"}).json()["id"]
    wedding_id = client.post(
        "/weddings",
        json={
            "client_id": client_id,
            "wedding_date": "2026-12-01",
            "address": "123 Main Street",
        },
    ).json()["id"]
    pricing_id = _save_pricing(client, _pricing_payload("Validation"))["id"]

    response = client.post(
        f"/weddings/{wedding_id}/invoice",
        json={"pricing_version_id": pricing_id},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "address" not in detail
    assert "ready_by" in detail
    assert "miles_one_way" in detail


def test_invalid_values_are_rejected(client):
    client_id = client.post("/clients", json={"name": "Invalid Check"}).json()["id"]
    wedding_id = client.post(
        "/weddings",
        json={
            "client_id": client_id,
            "wedding_date": "2026-12-01",
            "address": "123 Main Street",
            "status": 1,
        },
    ).json()["id"]

    wedding_invalid = client.post(
        "/weddings",
        json={
            "client_id": client_id,
            "wedding_date": "2026-12-01",
            "status": 9,
        },
    )
    assert wedding_invalid.status_code == 422

    party_invalid = client.post(
        f"/weddings/{wedding_id}/party-members",
        json={
            "role": "X",
            "hairstyle": "U",
            "by_me_quantity": 0,
            "by_assistant_quantity": 0,
        },
    )
    assert party_invalid.status_code == 422

    hairstyle_invalid = client.post(
        f"/weddings/{wedding_id}/party-members",
        json={
            "role": "P",
            "hairstyle": "X",
            "by_me_quantity": 0,
            "by_assistant_quantity": 0,
        },
    )
    assert hairstyle_invalid.status_code == 422

    negative_quantity = client.post(
        f"/weddings/{wedding_id}/party-members",
        json={
            "role": "P",
            "hairstyle": "U",
            "by_me_quantity": -1,
            "by_assistant_quantity": 0,
        },
    )
    assert negative_quantity.status_code == 422


def test_nonexistent_foreign_key_rejected(client):
    wedding_missing_client = client.post(
        "/weddings",
        json={
            "client_id": 9999,
            "wedding_date": "2026-12-01",
            "address": "123 Main Street",
            "status": 1,
        },
    )
    assert wedding_missing_client.status_code == 404

    payment_missing_wedding = client.post(
        "/payments",
        json={
            "wedding_id": 9999,
            "amount": "10.00",
            "payment_date": "2026-12-01",
            "payment_method": "cash",
        },
    )
    assert payment_missing_wedding.status_code == 404


def test_schema_initializes_successfully(tmp_path):
    db_path = tmp_path / "schema.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path}"
    src_path = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = os.pathsep.join(
        path for path in (src_path, env.get("PYTHONPATH")) if path
    )
    result = subprocess.run(
        [sys.executable, "-m", "client_dashboard.scripts.init_db"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Verified tables" in result.stdout
    assert db_path.exists()
