from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from importlib import import_module
from zoneinfo import ZoneInfo

import pytest

from client_dashboard.api.schemas import PricingVersionBase
from client_dashboard.models import PricingVersion
from client_dashboard.pricing import build_preview


DENVER = ZoneInfo("America/Denver")


def pricing_payload(name: str = "Spring 2026", **overrides):
    payload = {
        "name": name,
        "bride_price": "120.00",
        "trial_price": "110.00",
        "bridesmaid_price": "90.00",
        "flowergirl_price": "45.00",
        "early_morning_fee": "40.00",
        "assistant_fee": "150.00",
        "assistant_bridesmaid_cut": "125.00",
        "base_travel_fee": "25.00",
        "travel_fee": "0.75",
        "deposit_percentage": "50.00",
        "travel_discount_percentage": "20.00",
        "assistant_travel_fee_cut": "15.00",
        "bride_duration_minutes": 75,
        "bridesmaid_updo_duration_minutes": 30,
        "bridesmaid_down_duration_minutes": 45,
        "flowergirl_duration_minutes": 0,
    }
    payload.update(overrides)
    return payload


def preview(client, payload):
    response = client.post("/pricing-versions/save-preview", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert {
        "action",
        "current_default_id",
        "preview_date",
        "confirmation_fingerprint",
        "affected_records",
    } <= body.keys()
    return body


def confirmed_save(client, payload, preview_body=None):
    preview_body = preview_body or preview(client, payload)
    response = client.post(
        "/pricing-versions/save",
        json={
            **payload,
            "confirmed": True,
            "confirmation_fingerprint": preview_body["confirmation_fingerprint"],
        },
    )
    assert response.status_code in (200, 201), response.text
    return response.json()


def set_created_at(db_session_factory, pricing_id: int, value: datetime) -> None:
    with db_session_factory() as session:
        version = session.get(PricingVersion, pricing_id)
        assert version is not None
        version.created_at = value
        session.commit()


def create_invoice(client, pricing_id: int, *, name="Affected Client", status=1, archived=False):
    client_id = client.post(
        "/clients", json={"name": name, "archived": archived}
    ).json()["id"]
    wedding_id = client.post(
        "/weddings",
        json={
            "client_id": client_id,
            "wedding_date": "2026-10-10",
            "address": "123 Main Street",
            "miles_one_way": "10.00",
            "ready_by": "09:00:00",
            "status": status,
        },
    ).json()["id"]
    client.post(
        f"/weddings/{wedding_id}/party-members",
        json={"role": "P", "hairstyle": "U", "assistant": True},
    )
    response = client.post(
        f"/weddings/{wedding_id}/invoice", json={"pricing_version_id": pricing_id}
    )
    assert response.status_code == 201, response.text
    return client_id, wedding_id, response.json()["invoice"]


def test_pricing_workflow_is_the_only_public_write_contract(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "post" in paths["/pricing-versions/save-preview"]
    assert "post" in paths["/pricing-versions/save"]
    assert "post" not in paths["/pricing-versions"]
    assert "patch" not in paths["/pricing-versions/{pricing_version_id}"]


def test_complete_validation_and_invalid_requests_are_atomic(client):
    valid = pricing_payload()
    invalid_payloads = [
        {**valid, "name": "   "},
        {**valid, "name": "1234567890123456"},
        {key: value for key, value in valid.items() if key != "travel_fee"},
        {**valid, "bride_price": "-0.01"},
        {**valid, "assistant_bridesmaid_cut": "-0.01"},
        {**valid, "assistant_travel_fee_cut": "-0.01"},
        {**valid, "deposit_percentage": "100.01"},
        {**valid, "travel_discount_percentage": "-0.01"},
        {**valid, "bride_duration_minutes": -1},
        {**valid, "bridesmaid_updo_duration_minutes": 1.5},
    ]
    for payload in invalid_payloads:
        response = client.post("/pricing-versions/save-preview", json=payload)
        assert response.status_code == 422, (payload, response.text)

    # Zero-minute durations and flat assistant pay above 100 are valid.
    valid_preview = preview(client, valid)
    assert valid_preview["action"] == "create"
    assert client.get("/pricing-versions").json() == []


def test_names_are_trimmed_and_casefold_unique(client, db_session_factory):
    first = confirmed_save(client, pricing_payload("  Straße  "))["version"]
    assert first["name"] == "Straße"

    set_created_at(db_session_factory, first["id"], datetime.now(timezone.utc) - timedelta(days=8))
    second = confirmed_save(client, pricing_payload("Other"))["version"]
    assert second["id"] != first["id"]

    conflict = client.post(
        "/pricing-versions/save-preview", json=pricing_payload(" STRASSE ")
    )
    assert conflict.status_code == 409
    assert len(client.get("/pricing-versions").json()) == 2


def test_preview_confirmation_and_fingerprint_are_required(client):
    payload = pricing_payload()
    shown = preview(client, payload)
    assert client.get("/pricing-versions").json() == []

    unconfirmed = client.post(
        "/pricing-versions/save",
        json={**payload, "confirmed": False, "confirmation_fingerprint": shown["confirmation_fingerprint"]},
    )
    assert unconfirmed.status_code == 422

    changed = client.post(
        "/pricing-versions/save",
        json={
            **payload,
            "bride_price": "121.00",
            "confirmed": True,
            "confirmation_fingerprint": shown["confirmation_fingerprint"],
        },
    )
    assert changed.status_code == 409
    assert client.get("/pricing-versions").json() == []

    saved = confirmed_save(client, payload, shown)
    assert saved["action"] == "create"
    assert saved["version"]["revision"] == 1


def test_denver_calendar_day_seven_corrects_and_day_eight_creates(client, db_session_factory):
    first = confirmed_save(client, pricing_payload())["version"]
    today = datetime.now(DENVER).date()
    day_seven_creation = datetime.combine(today - timedelta(days=6), time(12), DENVER).astimezone(timezone.utc)
    set_created_at(db_session_factory, first["id"], day_seven_creation)

    correction_payload = pricing_payload("Corrected", bride_price="130.00")
    correction_preview = preview(client, correction_payload)
    assert correction_preview["action"] == "correct"
    corrected = confirmed_save(client, correction_payload, correction_preview)
    assert corrected["version"]["id"] == first["id"]
    assert corrected["version"]["created_at"] == first["created_at"] or corrected["version"]["created_date"] == (today - timedelta(days=6)).isoformat()
    assert corrected["version"]["revision"] == 2

    day_eight_creation = datetime.combine(today - timedelta(days=7), time(12), DENVER).astimezone(timezone.utc)
    set_created_at(db_session_factory, first["id"], day_eight_creation)
    create_preview = preview(client, pricing_payload("New default", bride_price="140.00"))
    assert create_preview["action"] == "create"
    created = confirmed_save(client, pricing_payload("New default", bride_price="140.00"), create_preview)
    assert created["version"]["id"] != first["id"]
    assert created["version"]["revision"] == 1


def test_assistant_pay_over_100_is_flat_money_per_assisted_service(client):
    version = confirmed_save(client, pricing_payload(assistant_bridesmaid_cut="125.00"))["version"]
    _, _, invoice = create_invoice(client, version["id"])
    receipt = client.get(f"/invoices/{invoice['id']}/assistant-receipt")
    assert receipt.status_code == 200
    assert receipt.json()["assisted_bridesmaid_count"] == 1
    assert receipt.json()["assisted_bridesmaid_pay"] == "125.00"


def test_name_only_correction_does_not_increment_revision_or_report_impacts(client):
    first = confirmed_save(client, pricing_payload())["version"]
    create_invoice(client, first["id"])

    renamed_payload = pricing_payload("Renamed")
    shown = preview(client, renamed_payload)
    assert shown["action"] == "correct"
    assert shown["affected_records"] == []
    renamed = confirmed_save(client, renamed_payload, shown)["version"]
    assert renamed["revision"] == 1

    invoice = client.get("/invoices").json()[0]
    assert invoice["pricing_revision_applied"] == 1
    assert invoice["pricing_stale"] is False


def test_calculation_correction_lists_every_reference_and_preserves_invoices(client):
    version = confirmed_save(client, pricing_payload())["version"]
    _, active_wedding, active_invoice = create_invoice(client, version["id"], name="Active")
    archived_client, archived_wedding, archived_invoice = create_invoice(
        client, version["id"], name="Archived Paid", status=6
    )
    client.patch(f"/clients/{archived_client}", json={"archived": True})
    client.post(
        "/payments",
        json={
            "wedding_id": archived_wedding,
            "amount": archived_invoice["grand_total"],
            "payment_date": "2026-09-01",
            "payment_method": "cash",
        },
    )

    payload = pricing_payload(bride_price="135.00")
    shown = preview(client, payload)
    impacts = shown["affected_records"]
    assert {row["invoice_id"] for row in impacts} == {active_invoice["id"], archived_invoice["id"]}
    archived = next(row for row in impacts if row["invoice_id"] == archived_invoice["id"])
    assert {
        "client_name", "wedding_id", "wedding_date", "workflow_status", "archived",
        "grand_total", "payment_total", "payment_state",
    } <= archived.keys()
    assert archived["archived"] is True
    assert archived["payment_state"] == "paid"

    before = {
        invoice["id"]: invoice
        for invoice in (client.get(f"/weddings/{active_wedding}/invoice").json(), client.get(f"/weddings/{archived_wedding}/invoice").json())
    }
    saved = confirmed_save(client, payload, shown)
    assert saved["version"]["revision"] == 2
    for wedding_id in (active_wedding, archived_wedding):
        invoice = client.get(f"/weddings/{wedding_id}/invoice").json()
        original = before[invoice["id"]]
        assert invoice["pricing_stale"] is True
        for field in ("grand_total", "calculation_hash", "calculation_snapshot", "line_items", "message_text"):
            assert invoice[field] == original[field]


def test_impact_context_change_invalidates_confirmation_without_partial_save(client):
    version = confirmed_save(client, pricing_payload())["version"]
    _, wedding_id, invoice = create_invoice(client, version["id"])
    payload = pricing_payload(bridesmaid_price="115.00")
    shown = preview(client, payload)

    payment = client.post(
        "/payments",
        json={
            "wedding_id": wedding_id,
            "amount": "10.00",
            "payment_date": "2026-09-01",
            "payment_method": "cash",
        },
    )
    assert payment.status_code == 201
    stale_confirmation = client.post(
        "/pricing-versions/save",
        json={
            **payload,
            "confirmed": True,
            "confirmation_fingerprint": shown["confirmation_fingerprint"],
        },
    )
    assert stale_confirmation.status_code == 409
    assert "preview" in stale_confirmation.json()["detail"].lower()

    unchanged_version = client.get(f"/pricing-versions/{version['id']}").json()
    unchanged_invoice = client.get(f"/invoices/{invoice['id']}").json()
    assert unchanged_version["revision"] == 1
    assert unchanged_invoice["pricing_stale"] is False


def test_stale_invoice_ignores_source_refresh_until_manual_regeneration(client):
    version = confirmed_save(client, pricing_payload())["version"]
    client_id, wedding_id, original = create_invoice(client, version["id"])
    corrected_payload = pricing_payload(bridesmaid_price="115.00")
    confirmed_save(client, corrected_payload)

    stale = client.get(f"/weddings/{wedding_id}/invoice").json()
    assert stale["pricing_stale"] is True
    client.patch(f"/clients/{client_id}", json={"name": "Latest Name"})
    client.patch(f"/weddings/{wedding_id}", json={"miles_one_way": "25.00"})
    client.post(
        f"/weddings/{wedding_id}/party-members",
        json={"role": "F", "hairstyle": "D"},
    )

    still_stale = client.get(f"/weddings/{wedding_id}/invoice").json()
    assert still_stale["pricing_stale"] is True
    assert still_stale["pricing_revision_applied"] == 1
    for field in ("grand_total", "calculation_hash", "calculation_snapshot", "message_text"):
        assert still_stale[field] == original[field]

    regenerated = client.post(
        f"/weddings/{wedding_id}/invoice", json={"pricing_version_id": version["id"]}
    )
    assert regenerated.status_code == 200
    refreshed = regenerated.json()["invoice"]
    assert refreshed["pricing_revision_applied"] == 2
    assert refreshed["pricing_stale"] is False
    assert refreshed["calculation_hash"] != original["calculation_hash"]
    assert "Latest Name" in refreshed["message_text"]


def test_delete_policy_and_default_promotion(client, db_session_factory):
    first = confirmed_save(client, pricing_payload("First"))["version"]
    sole_delete = client.delete(
        f"/pricing-versions/{first['id']}",
        params={"confirmed": True, "expected_default_id": first["id"]},
    )
    assert sole_delete.status_code == 409

    set_created_at(db_session_factory, first["id"], datetime.now(timezone.utc) - timedelta(days=8))
    second = confirmed_save(client, pricing_payload("Second"))["version"]
    create_invoice(client, first["id"])

    referenced = client.delete(
        f"/pricing-versions/{first['id']}",
        params={"confirmed": True, "expected_default_id": second["id"]},
    )
    assert referenced.status_code == 409
    assert client.delete(
        f"/pricing-versions/{second['id']}", params={"expected_default_id": second["id"]}
    ).status_code in (400, 422)
    stale_context = client.delete(
        f"/pricing-versions/{second['id']}",
        params={"confirmed": True, "expected_default_id": first["id"]},
    )
    assert stale_context.status_code == 409

    deleted = client.delete(
        f"/pricing-versions/{second['id']}",
        params={"confirmed": True, "expected_default_id": second["id"]},
    )
    assert deleted.status_code == 200
    assert deleted.json()["new_default"]["id"] == first["id"]


def test_pricing_read_metadata_and_newest_order_use_creation_time(client, db_session_factory):
    first = confirmed_save(client, pricing_payload("First"))["version"]
    set_created_at(db_session_factory, first["id"], datetime.now(timezone.utc) - timedelta(days=8))
    second = confirmed_save(client, pricing_payload("Second"))["version"]
    set_created_at(db_session_factory, first["id"], datetime.now(timezone.utc) + timedelta(minutes=1))

    versions = client.get("/pricing-versions").json()
    assert versions[0]["id"] == first["id"]
    assert versions[0]["is_default"] is True
    assert {"revision", "created_date", "correction_deadline", "can_delete", "reference_count"} <= versions[0].keys()
    assert versions[1]["is_default"] is False


@pytest.mark.parametrize(
    ("created_local", "day_seven", "day_eight"),
    [
        (
            datetime(2026, 3, 2, 0, 0, tzinfo=DENVER),
            datetime(2026, 3, 8, 23, 59, tzinfo=DENVER),
            datetime(2026, 3, 9, 0, 0, tzinfo=DENVER),
        ),
        (
            datetime(2026, 10, 26, 0, 0, tzinfo=DENVER),
            datetime(2026, 11, 1, 23, 59, tzinfo=DENVER),
            datetime(2026, 11, 2, 0, 0, tzinfo=DENVER),
        ),
    ],
)
def test_persisted_sqlite_timestamp_uses_denver_day_seven_boundary_across_dst(
    client, db_session_factory, created_local, day_seven, day_eight
):
    version = confirmed_save(client, pricing_payload())["version"]
    set_created_at(db_session_factory, version["id"], created_local.astimezone(timezone.utc))
    data = PricingVersionBase.model_validate(pricing_payload(bride_price="130.00")).model_dump()

    # A new session proves SQLite's committed timestamp has been closed/reopened
    # and read back without timezone information.
    with db_session_factory() as session:
        persisted = session.get(PricingVersion, version["id"])
        assert persisted.created_at.tzinfo is None
        assert build_preview(session, data, now=day_seven)["action"] == "correct"
    with db_session_factory() as session:
        next_version = {**data, "name": "Next version"}
        assert build_preview(session, next_version, now=day_eight)["action"] == "create"


def submit_confirmation(client, payload, shown):
    return client.post(
        "/pricing-versions/save",
        json={
            **payload,
            "confirmed": True,
            "confirmation_fingerprint": shown["confirmation_fingerprint"],
        },
    )


def test_another_pricing_save_invalidates_confirmation(client):
    confirmed_save(client, pricing_payload())
    payload = pricing_payload(bride_price="130.00")
    shown = preview(client, payload)
    confirmed_save(client, pricing_payload("Intervening"))
    assert submit_confirmation(client, payload, shown).status_code == 409


def test_added_or_removed_invoice_invalidates_confirmation(client):
    version = confirmed_save(client, pricing_payload())["version"]
    payload = pricing_payload(bride_price="130.00")

    before_add = preview(client, payload)
    _, wedding_id, _ = create_invoice(client, version["id"])
    assert submit_confirmation(client, payload, before_add).status_code == 409

    before_remove = preview(client, payload)
    assert client.delete(f"/weddings/{wedding_id}").status_code == 204
    assert submit_confirmation(client, payload, before_remove).status_code == 409


def test_invoice_regeneration_and_workflow_context_invalidate_confirmation(client):
    version = confirmed_save(client, pricing_payload())["version"]
    client_id, wedding_id, _ = create_invoice(client, version["id"])
    payload = pricing_payload(bride_price="130.00")

    before_regeneration = preview(client, payload)
    assert client.post(
        f"/weddings/{wedding_id}/invoice", json={"pricing_version_id": version["id"]}
    ).status_code == 200
    assert submit_confirmation(client, payload, before_regeneration).status_code == 409

    before_workflow_change = preview(client, payload)
    assert client.patch(f"/weddings/{wedding_id}", json={"status": 6}).status_code == 200
    assert client.get(f"/clients/{client_id}").json()["archived"] is True
    assert submit_confirmation(client, payload, before_workflow_change).status_code == 409


def test_stale_party_update_and_delete_preserve_invoice_and_receipt(client):
    version = confirmed_save(client, pricing_payload())["version"]
    _, wedding_id, original = create_invoice(client, version["id"])
    original_receipt = client.get(f"/invoices/{original['id']}/assistant-receipt").json()
    member = client.get(f"/weddings/{wedding_id}/party-members").json()[0]
    confirmed_save(client, pricing_payload(bridesmaid_price="115.00"))

    assert client.patch(
        f"/party-members/{member['id']}", json={"hairstyle": "D"}
    ).status_code == 200
    assert client.delete(f"/party-members/{member['id']}").status_code == 204
    assert client.get(f"/weddings/{wedding_id}/party-members").json() == []

    unchanged = client.get(f"/weddings/{wedding_id}/invoice").json()
    assert unchanged["pricing_stale"] is True
    for field in ("grand_total", "calculation_hash", "calculation_snapshot", "message_text"):
        assert unchanged[field] == original[field]
    assert client.get(f"/invoices/{original['id']}/assistant-receipt").json() == original_receipt


def test_nonstale_party_update_and_delete_continue_to_refresh_invoice(client):
    version = confirmed_save(client, pricing_payload())["version"]
    _, wedding_id, original = create_invoice(client, version["id"])
    member = client.get(f"/weddings/{wedding_id}/party-members").json()[0]

    assert client.patch(
        f"/party-members/{member['id']}", json={"assistant": False}
    ).status_code == 200
    after_update = client.get(f"/weddings/{wedding_id}/invoice").json()
    assert after_update["pricing_stale"] is False
    assert after_update["calculation_hash"] != original["calculation_hash"]
    assert client.get(f"/invoices/{original['id']}/assistant-receipt").status_code == 404

    assert client.delete(f"/party-members/{member['id']}").status_code == 204
    after_delete = client.get(f"/weddings/{wedding_id}/invoice").json()
    assert after_delete["calculation_hash"] != after_update["calculation_hash"]
    assert after_delete["pricing_stale"] is False


def test_default_invoice_generation_uses_created_at_order(client, db_session_factory):
    first = confirmed_save(client, pricing_payload("First"))["version"]
    set_created_at(db_session_factory, first["id"], datetime.now(timezone.utc) - timedelta(days=8))
    second = confirmed_save(client, pricing_payload("Second"))["version"]
    set_created_at(db_session_factory, first["id"], datetime.now(timezone.utc) + timedelta(minutes=1))
    _, wedding_id, _ = create_invoice(client, second["id"])

    generated = client.post(f"/weddings/{wedding_id}/invoice", json={})
    assert generated.status_code == 200
    assert generated.json()["invoice"]["pricing_version_id"] == first["id"]


def test_naive_database_timestamps_are_treated_as_utc_across_dst():
    pricing = import_module("client_dashboard.pricing")
    for value in (
        datetime(2026, 3, 8, 8, 30),
        datetime(2026, 11, 1, 7, 30),
    ):
        converted = pricing.as_utc(value)
        assert converted.tzinfo is timezone.utc
        assert converted == value.replace(tzinfo=timezone.utc)
    aware = datetime(2026, 3, 8, 1, 30, tzinfo=DENVER)
    assert pricing.as_utc(aware) == aware.astimezone(timezone.utc)
