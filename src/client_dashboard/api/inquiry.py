from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from .deps import get_db
from .schemas import PublicInquiryCreate
from ..models import Client, InquiryAttempt, Wedding, WeddingPartyMember, WeddingStatusProgress
from ..settings import get_settings

router = APIRouter()
DENVER = ZoneInfo("America/Denver")
WINDOW = timedelta(minutes=60)
LIMIT = 3
SUCCESS_MESSAGE = "I've received your inquiry and will be in touch within 2 business days. I can't wait to chat details with you soon!!"


def denver_today() -> date:
    return datetime.now(DENVER).date()


def date_limit(today: date) -> date:
    try:
        return today.replace(year=today.year + 1)
    except ValueError:
        return today.replace(year=today.year + 1, day=28)


def _validate_date(value: date) -> None:
    today = denver_today()
    if value <= today or value > date_limit(today):
        raise HTTPException(status_code=422, detail="Choose a wedding date after today and within one year")


def _lock_ip_attempts(session: Session, ip_address: str) -> None:
    connection = session.connection()
    if connection.dialect.name == "sqlite":
        # Serialize count-and-insert across workers using SQLite's write lock.
        connection.exec_driver_sql("BEGIN IMMEDIATE")
    elif connection.dialect.name == "postgresql":
        connection.execute(text("SELECT pg_advisory_xact_lock(hashtext(:ip_address))"), {"ip_address": ip_address})


def _check_rate_limit(session: Session, ip_address: str, now: datetime) -> None:
    _lock_ip_attempts(session, ip_address)
    since = now - WINDOW
    session.execute(delete(InquiryAttempt).where(InquiryAttempt.attempted_at <= since))
    count = session.scalar(
        select(func.count(InquiryAttempt.id)).where(
            InquiryAttempt.ip_address == ip_address,
            InquiryAttempt.attempted_at > since,
        )
    ) or 0
    session.add(InquiryAttempt(ip_address=ip_address, attempted_at=now))
    session.flush()
    if count >= LIMIT:
        session.commit()
        raise HTTPException(status_code=429, detail="Inquiry limit reached. Please try again in an hour.")


def _context_notes(payload: PublicInquiryCreate) -> str | None:
    notes = [
        "Getting-ready location: home" if payload.location_type == "home" else "Getting-ready location: venue",
        "Ready-by time is firm" if payload.time_firmness == "firm" else "Ready-by time is an estimate",
        "Interested in a bridal trial" if payload.bridal_trial == "yes" else "Still considering a bridal trial",
    ]
    if payload.additional_notes and payload.additional_notes.strip():
        notes.append(payload.additional_notes.strip())
    return "\n".join(notes)


def _add_members(session: Session, wedding: Wedding, payload: PublicInquiryCreate) -> None:
    for _ in range(payload.bride_count):
        session.add(WeddingPartyMember(
            wedding_id=wedding.id,
            role=WeddingPartyMember.ROLE_BRIDE,
            hairstyle=WeddingPartyMember.HAIRSTYLE_UPDO,
            assistant=False,
        ))
    for role, count in (
        (WeddingPartyMember.ROLE_BRIDAL_PARTY, payload.party_count),
        (WeddingPartyMember.ROLE_JUNIOR_BRIDESMAID, payload.junior_count),
    ):
        for _ in range(count):
            session.add(WeddingPartyMember(
                wedding_id=wedding.id,
                role=role,
                hairstyle=WeddingPartyMember.HAIRSTYLE_DOWN,
                assistant=False,
            ))


@router.post("/api/inquiry", status_code=status.HTTP_201_CREATED)
def submit_inquiry(payload: PublicInquiryCreate, request: Request, session: Session = Depends(get_db)):
    if payload.website:
        raise HTTPException(status_code=400, detail="We couldn't submit your inquiry. Please review the form and try again.")
    _validate_date(payload.wedding_date)
    ip_address = request.client.host if request.client else "unknown"
    now = datetime.now(timezone.utc)
    try:
        if get_settings().environment != "development":
            _check_rate_limit(session, ip_address, now)
        source = payload.referral_other.strip() if payload.referral_source == "Other" else payload.referral_source
        client = Client(
            name=payload.name,
            email=payload.email,
            phone=payload.phone,
            social_media=payload.social_media,
            source=source,
            inquiry_date=denver_today(),
            notes=_context_notes(payload),
            planning_stage=payload.planning_stage,
            makeup_interest=payload.makeup_interest,
            recommendations_if_unavailable=payload.recommendations_if_unavailable,
            referral_name=payload.referral_name,
            is_referral=False,
        )
        session.add(client)
        session.flush()
        wedding = Wedding(
            client_id=client.id,
            wedding_date=payload.wedding_date,
            address=payload.address,
            ready_by=payload.ready_by,
            status=Wedding.STATUS_INQUIRED,
            bridal_trial_status=Wedding.BRIDAL_TRIAL_INTERESTED,
        )
        session.add(wedding)
        session.flush()
        session.add(WeddingStatusProgress(
            wedding_id=wedding.id,
            status=wedding.status,
            forward_entered_at=wedding.created_at,
        ))
        _add_members(session, wedding, payload)
        session.commit()
    except HTTPException:
        raise
    except Exception:
        session.rollback()
        raise
    return {"message": SUCCESS_MESSAGE, "client_id": client.id, "wedding_id": wedding.id}
