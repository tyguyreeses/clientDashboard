from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, selectinload

from .models import Client, Invoice, Payment, PricingVersion, Wedding

DENVER = ZoneInfo("America/Denver")
PRICING_CALCULATION_FIELDS = (
    "bride_price", "trial_price", "bridesmaid_price", "flowergirl_price",
    "early_morning_fee", "assistant_fee", "assistant_cut", "assistant_bridesmaid_cut",
    "base_travel_fee", "travel_fee", "deposit_percentage",
    "travel_discount_percentage", "bride_duration_minutes",
    "bridesmaid_updo_duration_minutes", "bridesmaid_down_duration_minutes",
    "flowergirl_duration_minutes",
)


def normalize_pricing_name(value: str) -> str:
    return value.strip().casefold()


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def denver_date(value: datetime) -> date:
    return as_utc(value).astimezone(DENVER).date()


def newest_statement():
    return select(PricingVersion).order_by(PricingVersion.created_at.desc(), PricingVersion.id.desc())


def newest_pricing(session: Session) -> PricingVersion | None:
    return session.scalars(newest_statement().limit(1)).first()


def is_correction(version: PricingVersion, today: date) -> bool:
    return today <= denver_date(version.created_at) + timedelta(days=6)


def _decimal(value: Decimal | int | str) -> str:
    return format(Decimal(value), "f")


def pricing_values(version: PricingVersion) -> dict:
    return {field: getattr(version, field) for field in PRICING_CALCULATION_FIELDS}


def calculation_changed(version: PricingVersion, data: dict) -> bool:
    return any(getattr(version, field) != data[field] for field in PRICING_CALCULATION_FIELDS)


def ensure_unique_name(session: Session, normalized: str, target_id: int | None = None):
    statement = select(PricingVersion.id).where(PricingVersion.name_normalized == normalized)
    if target_id is not None:
        statement = statement.where(PricingVersion.id != target_id)
    if session.scalar(statement.limit(1)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pricing name already exists")


def correction_impacts(session: Session, version_id: int) -> list[dict]:
    invoices = session.scalars(
        select(Invoice)
        .options(selectinload(Invoice.wedding).selectinload(Wedding.client))
        .where(Invoice.pricing_version_id == version_id)
        .order_by(Invoice.id)
    ).all()
    if not invoices:
        return []
    totals = dict(session.execute(
        select(Payment.wedding_id, func.coalesce(func.sum(Payment.amount), 0))
        .where(Payment.wedding_id.in_([invoice.wedding_id for invoice in invoices]))
        .group_by(Payment.wedding_id)
    ).all())
    result = []
    for invoice in invoices:
        paid = Decimal(totals.get(invoice.wedding_id, 0))
        state = "unpaid" if paid <= 0 else "paid" if paid >= invoice.grand_total else "partial"
        wedding = invoice.wedding
        result.append({
            "invoice_id": invoice.id,
            "pricing_revision_applied": invoice.pricing_revision_applied,
            # Included in the fingerprint context (filtered from the public DTO)
            # so an explicit regeneration invalidates an outstanding confirmation.
            "invoice_updated_at": as_utc(invoice.updated_at).isoformat(),
            "client_name": wedding.client.name,
            "wedding_id": wedding.id,
            "wedding_date": wedding.wedding_date.isoformat(),
            "workflow_status": wedding.status,
            "archived": wedding.client.archived,
            "grand_total": _decimal(invoice.grand_total),
            "payment_total": _decimal(paid),
            "payment_state": state,
        })
    return result


def _canonical_payload(data: dict) -> dict:
    return {
        key: (_decimal(value) if isinstance(value, Decimal) else value)
        for key, value in sorted(data.items())
    }


def _fingerprint(context: dict) -> str:
    encoded = json.dumps(context, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_preview(session: Session, data: dict, now: datetime | None = None) -> dict:
    now = as_utc(now or datetime.now(timezone.utc))
    today = now.astimezone(DENVER).date()
    current = newest_pricing(session)
    action = "correct" if current and is_correction(current, today) else "create"
    target = current if action == "correct" else None
    normalized = normalize_pricing_name(data["name"])
    ensure_unique_name(session, normalized, target.id if target else None)
    changed = bool(target and calculation_changed(target, data))
    impacts = correction_impacts(session, target.id) if changed else []
    deadline = denver_date(target.created_at) + timedelta(days=6) if target else None
    context = {
        "payload": _canonical_payload({**data, "name": data["name"].strip(), "name_normalized": normalized}),
        "preview_date": today.isoformat(),
        "action": action,
        "current_default_id": current.id if current else None,
        "target_id": target.id if target else None,
        "target_revision": target.revision if target else None,
        "target_created_at": as_utc(target.created_at).isoformat() if target else None,
        "target_values": _canonical_payload(
            {"name": target.name, **pricing_values(target)}
        ) if target else None,
        "affected_records": impacts,
    }
    return {
        "action": action,
        "target_id": target.id if target else None,
        "target_revision": target.revision if target else None,
        "current_default_id": current.id if current else None,
        "preview_date": today.isoformat(),
        "correction_deadline": deadline.isoformat() if deadline else None,
        "affected_records": impacts,
        "confirmation_fingerprint": _fingerprint(context),
    }


def save_pricing(session: Session, data: dict, fingerprint: str) -> tuple[PricingVersion, dict]:
    # SQLite's application deployment uses one writer; lock before recomputing context.
    session.execute(text("BEGIN IMMEDIATE"))
    preview = build_preview(session, data)
    if preview["confirmation_fingerprint"] != fingerprint:
        session.rollback()
        raise HTTPException(status_code=409, detail="Pricing confirmation is stale; preview again")
    normalized = normalize_pricing_name(data["name"])
    if preview["action"] == "correct":
        version = session.get(PricingVersion, preview["target_id"])
        assert version is not None
        changed = calculation_changed(version, data)
        ensure_unique_name(session, normalized, version.id)
        for field, value in data.items():
            setattr(version, field, value.strip() if field == "name" else value)
        version.name_normalized = normalized
        if changed:
            version.revision += 1
    else:
        ensure_unique_name(session, normalized)
        values = {**data, "name": data["name"].strip()}
        version = PricingVersion(**values, name_normalized=normalized, revision=1)
        session.add(version)
    session.commit()
    session.refresh(version)
    return version, preview


def pricing_metadata(session: Session, version: PricingVersion, default_id: int | None = None) -> dict:
    if default_id is None:
        current = newest_pricing(session)
        default_id = current.id if current else None
    references = session.scalar(select(func.count(Invoice.id)).where(Invoice.pricing_version_id == version.id)) or 0
    count = session.scalar(select(func.count(PricingVersion.id))) or 0
    created = denver_date(version.created_at)
    can_delete = count > 1 and references == 0
    reason = None if can_delete else "sole_version" if count <= 1 else "referenced"
    return {
        **{column.name: getattr(version, column.name) for column in PricingVersion.__table__.columns if column.name != "name_normalized"},
        "is_default": version.id == default_id,
        "created_date": created.isoformat(),
        "correction_deadline": (created + timedelta(days=6)).isoformat(),
        "can_delete": can_delete,
        "delete_block_reason": reason,
        "reference_count": references,
    }


def delete_pricing(session: Session, version_id: int, expected_default_id: int) -> dict:
    session.execute(text("BEGIN IMMEDIATE"))
    versions = list(session.scalars(newest_statement()))
    if not versions:
        session.rollback()
        raise HTTPException(status_code=404, detail="Pricing version not found")
    current = versions[0]
    if current.id != expected_default_id:
        session.rollback()
        raise HTTPException(status_code=409, detail="Pricing default changed; reload and confirm again")
    target = next((version for version in versions if version.id == version_id), None)
    if target is None:
        session.rollback()
        raise HTTPException(status_code=404, detail="Pricing version not found")
    if len(versions) == 1:
        session.rollback()
        raise HTTPException(status_code=409, detail="The sole pricing version cannot be deleted")
    if session.scalar(select(Invoice.id).where(Invoice.pricing_version_id == version_id).limit(1)):
        session.rollback()
        raise HTTPException(status_code=409, detail="Pricing version is referenced by one or more invoices")
    session.delete(target)
    session.commit()
    new_default = newest_pricing(session)
    return {"deleted_id": version_id, "new_default": pricing_metadata(session, new_default) if new_default else None}
