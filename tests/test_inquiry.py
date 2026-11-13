from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import event, func, select, update

from client_dashboard.api import inquiry as inquiry_api
from client_dashboard.models import Client, InquiryAttempt, Wedding, WeddingPartyMember, WeddingStatusProgress


def inquiry_payload(**updates):
    payload = {
        "name": "Taylor Bride",
        "email": "taylor@example.com",
        "social_media": "@taylor",
        "wedding_date": (inquiry_api.denver_today() + timedelta(days=30)).isoformat(),
        "address": "123 Main Street",
        "ready_by": "10:30",
        "time_firmness": "firm",
        "location_type": "home",
        "makeup_interest": True,
        "bridal_trial": "yes",
        "planning_stage": "invoice",
        "recommendations_if_unavailable": False,
        "referral_source": "Instagram",
        "contact_consent": True,
    }
    payload.update(updates)
    return payload


def test_public_inquiry_endpoint_is_available_anonymously_and_validates_input(anonymous_client, db_session_factory):
    response = anonymous_client.post("/api/inquiry", json={})

    assert response.status_code == 422
    with db_session_factory() as db:
        assert db.scalar(select(Client.id).limit(1)) is None
        assert db.scalar(select(Wedding.id).limit(1)) is None
        assert db.scalar(select(WeddingPartyMember.id).limit(1)) is None


def test_valid_public_submission_creates_related_records_and_maps_answers(anonymous_client, db_session_factory):
    payload = inquiry_payload(bride_count=0, party_count=2, junior_count=1, referral_source="Other", referral_other="Local fair", referral_name="Avery", additional_notes="Sensitive to fragrance", bridal_trial="thinking")
    response = anonymous_client.post("/api/inquiry", json=payload)

    assert response.status_code == 201, response.text
    with db_session_factory() as db:
        client = db.scalar(select(Client))
        wedding = db.scalar(select(Wedding))
        members = list(db.scalars(select(WeddingPartyMember).order_by(WeddingPartyMember.id)))
        progress = list(db.scalars(select(WeddingStatusProgress)))
        assert client is not None and wedding is not None
        assert client.source == "Local fair"
        assert client.referral_name == "Avery"
        assert client.planning_stage == "invoice"
        assert client.inquiry_date == inquiry_api.denver_today()
        assert "Sensitive to fragrance" in client.notes
        assert "Still considering a bridal trial" in client.notes
        assert "Local fair" not in client.notes
        assert wedding.status == Wedding.STATUS_INQUIRED
        assert wedding.bridal_trial_status == Wedding.BRIDAL_TRIAL_INTERESTED
        assert [member.role for member in members] == ["P", "P", "F"]
        assert len(progress) == 1 and progress[0].status == Wedding.STATUS_INQUIRED
        assert response.json()["message"].startswith("I've received your inquiry")


def test_duplicate_valid_submissions_create_separate_records(anonymous_client, db_session_factory):
    first = anonymous_client.post("/api/inquiry", json=inquiry_payload())
    second = anonymous_client.post("/api/inquiry", json=inquiry_payload())

    assert first.status_code == second.status_code == 201
    assert first.json()["client_id"] != second.json()["client_id"]
    with db_session_factory() as db:
        assert db.scalar(select(func.count(Client.id))) == 2
        assert db.scalar(select(func.count(Wedding.id))) == 2


def test_planning_choices_round_trip_through_authenticated_client_api(client):
    for choice in ("looking", "invoice", "book"):
        submitted = client.post("/api/inquiry", json=inquiry_payload(planning_stage=choice))
        assert submitted.status_code == 201, submitted.text
        readback = client.get(f"/clients/{submitted.json()['client_id']}")
        assert readback.status_code == 200, readback.text
        assert readback.json()["planning_stage"] == choice


def test_source_and_additional_notes_limits_are_enforced(anonymous_client):
    too_long_source = anonymous_client.post("/api/inquiry", json=inquiry_payload(referral_source="Other", referral_other="x" * 101))
    too_long_notes = anonymous_client.post("/api/inquiry", json=inquiry_payload(additional_notes="x" * 2001))
    valid_limits = anonymous_client.post("/api/inquiry", json=inquiry_payload(referral_source="Other", referral_other="x" * 100, additional_notes="x" * 2000))

    assert too_long_source.status_code == 422
    assert too_long_notes.status_code == 422
    assert valid_limits.status_code == 201


def test_future_dates_and_whole_number_service_counts_are_validated(anonymous_client, monkeypatch):
    monkeypatch.setattr(inquiry_api, "denver_today", lambda: date(2028, 2, 29))
    far_future = anonymous_client.post("/api/inquiry", json=inquiry_payload(wedding_date="2035-01-01"))
    today = anonymous_client.post("/api/inquiry", json=inquiry_payload(wedding_date="2028-02-29"))
    fractional = anonymous_client.post("/api/inquiry", json=inquiry_payload(bride_count=1.5))
    excessive = anonymous_client.post("/api/inquiry", json=inquiry_payload(bride_count=10, party_count=1))

    assert far_future.status_code == 201
    assert today.status_code == 422
    assert fractional.status_code == 422
    assert excessive.status_code == 422


def test_fourth_request_per_ip_is_rejected_without_business_records(anonymous_client, db_session_factory):
    responses = [anonymous_client.post("/api/inquiry", json=inquiry_payload()) for _ in range(4)]

    assert [response.status_code for response in responses] == [201, 201, 201, 429]
    with db_session_factory() as db:
        assert db.scalar(select(func.count(Client.id))) == 3
        assert db.scalar(select(func.count(Wedding.id))) == 3
        assert db.scalar(select(func.count(InquiryAttempt.id))) == 4


def test_rate_limit_expires_after_rolling_hour(anonymous_client, db_session_factory):
    for _ in range(3):
        assert anonymous_client.post("/api/inquiry", json=inquiry_payload()).status_code == 201
    assert anonymous_client.post("/api/inquiry", json=inquiry_payload()).status_code == 429
    with db_session_factory() as db:
        db.execute(update(InquiryAttempt).values(attempted_at=datetime.now(timezone.utc) - timedelta(minutes=61)))
        db.commit()

    assert anonymous_client.post("/api/inquiry", json=inquiry_payload()).status_code == 201


def test_concurrent_requests_are_limited_and_forwarded_headers_cannot_choose_ip(anonymous_client, db_session_factory):
    def submit(index):
        return anonymous_client.post(
            "/api/inquiry",
            json=inquiry_payload(name=f"Bride {index}"),
            headers={"X-Forwarded-For": f"198.51.100.{index}"},
        ).status_code

    with ThreadPoolExecutor(max_workers=4) as pool:
        statuses = list(pool.map(submit, range(4)))

    assert statuses.count(201) == 3
    assert statuses.count(429) == 1
    with db_session_factory() as db:
        assert db.scalar(select(func.count(Client.id))) == 3
        assert len(set(db.scalars(select(InquiryAttempt.ip_address)))) == 1


def test_development_environment_is_exempt_from_the_limit(anonymous_client, monkeypatch):
    monkeypatch.setattr(inquiry_api, "get_settings", lambda: SimpleNamespace(environment="development"))

    responses = [anonymous_client.post("/api/inquiry", json=inquiry_payload()) for _ in range(4)]

    assert all(response.status_code == 201 for response in responses)


def test_persistence_failure_rolls_back_every_business_record(anonymous_client, db_session_factory):
    def fail_party_insert(mapper, connection, member):
        raise RuntimeError("simulated database failure")

    event.listen(WeddingPartyMember, "before_insert", fail_party_insert)
    try:
        with pytest.raises(RuntimeError, match="simulated database failure"):
            anonymous_client.post("/api/inquiry", json=inquiry_payload())
    finally:
        event.remove(WeddingPartyMember, "before_insert", fail_party_insert)

    with db_session_factory() as db:
        assert db.scalar(select(func.count(Client.id))) == 0
        assert db.scalar(select(func.count(Wedding.id))) == 0
        assert db.scalar(select(func.count(WeddingPartyMember.id))) == 0
        assert db.scalar(select(func.count(WeddingStatusProgress.id))) == 0


def test_consent_and_honeypot_rejections_create_no_records(anonymous_client, db_session_factory):
    no_consent = anonymous_client.post("/api/inquiry", json=inquiry_payload(contact_consent=False))
    honeypot = anonymous_client.post("/api/inquiry", json=inquiry_payload(website="bot-filled"))

    assert no_consent.status_code == 422
    assert honeypot.status_code == 400
    with db_session_factory() as db:
        assert db.scalar(select(func.count(Client.id))) == 0
        assert db.scalar(select(func.count(Wedding.id))) == 0
