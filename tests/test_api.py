from __future__ import annotations

import os
import subprocess
import sys
from decimal import Decimal

from client_dashboard.models import Invoice, Payment


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
            "location": "Denver, CO",
            "miles_one_way": "24.50",
            "ready_by": "08:30:00",
            "status": 1,
            "bridal_trial": True,
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


def test_pricing_versions_and_invoices(client, db_session_factory):
    pricing_response = client.post(
        "/pricing-versions",
        json={
            "name": "2026 baseline",
            "bride_price": "250.00",
            "trial_price": "100.00",
            "bridesmaid_price": "125.00",
            "flowergirl_price": "65.00",
            "early_morning_fee": "50.00",
            "assistant_fee": "150.00",
            "assistant_bridesmaid_cut": "20.00",
            "base_travel_fee": "30.00",
            "travel_fee": "1.25",
            "deposit_percentage": "50.00",
            "travel_discount_percentage": "10.00",
        },
    )
    assert pricing_response.status_code == 201
    pricing_version_id = pricing_response.json()["id"]

    pricing_get = client.get(f"/pricing-versions/{pricing_version_id}")
    assert pricing_get.status_code == 200
    assert pricing_get.json()["name"] == "2026 baseline"

    client_id = client.post("/clients", json={"name": "Zoe Reed"}).json()["id"]
    wedding_id = client.post(
        "/weddings",
        json={
            "client_id": client_id,
            "wedding_date": "2026-11-01",
            "status": 2,
        },
    ).json()["id"]

    with db_session_factory() as session:
        invoice = Invoice(
            wedding_id=wedding_id,
            version_number=1,
            pricing_version_id=pricing_version_id,
            services_total=Decimal("500.00"),
            travel_total=Decimal("30.00"),
            discount_total=Decimal("0.00"),
            deposit_amount=Decimal("250.00"),
            balance_due=Decimal("280.00"),
            grand_total=Decimal("560.00"),
        )
        session.add(invoice)
        session.commit()
        invoice_id = invoice.id

    invoice_get = client.get(f"/invoices/{invoice_id}")
    assert invoice_get.status_code == 200
    assert invoice_get.json()["version_number"] == 1
    assert invoice_get.json()["pricing_version"]["id"] == pricing_version_id

    wedding_invoice = client.get(f"/weddings/{wedding_id}/invoice")
    assert wedding_invoice.status_code == 200
    assert wedding_invoice.json()["id"] == invoice_id

    invoice_list = client.get("/invoices")
    assert invoice_list.status_code == 200
    assert len(invoice_list.json()) == 1


def test_invalid_values_are_rejected(client):
    client_id = client.post("/clients", json={"name": "Invalid Check"}).json()["id"]
    wedding_id = client.post(
        "/weddings",
        json={
            "client_id": client_id,
            "wedding_date": "2026-12-01",
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
    result = subprocess.run(
        [sys.executable, "-m", "client_dashboard.scripts.init_db"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Verified tables" in result.stdout
    assert db_path.exists()
