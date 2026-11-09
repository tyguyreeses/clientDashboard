from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models import AuditEvent, AuthSession, RateLimitBucket, User
from ..settings import get_settings


def now() -> datetime:
    return datetime.now(timezone.utc)


def token_hash(value: str) -> str:
    return hmac.new(get_settings().session_secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def create_session(db: Session, user: User) -> tuple[str, str, AuthSession]:
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    expiry = now() + timedelta(hours=24)
    active = list(db.scalars(select(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)).order_by(AuthSession.created_at)))
    for previous in active[:-4]:
        previous.revoked_at = now()
    session = AuthSession(user_id=user.id, token_hash=token_hash(token), csrf_hash=token_hash(csrf), expires_at=expiry, last_seen_at=now())
    db.add(session)
    return token, csrf, session


def revoke(db: Session, session: AuthSession | None):
    if session and session.revoked_at is None:
        session.revoked_at = now()


def revoke_all(db: Session, user_id: int):
    for session in db.scalars(select(AuthSession).where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))):
        session.revoked_at = now()


def audit(db: Session, event: str, outcome: str, user_id: int | None = None):
    db.add(AuditEvent(user_id=user_id, event=event, outcome=outcome, metadata_json={}))


def cleanup(db: Session):
    cutoff = now() - timedelta(days=90)
    db.execute(delete(AuditEvent).where(AuditEvent.created_at < cutoff))
    db.execute(delete(AuthSession).where(AuthSession.expires_at < now()))
    db.execute(delete(RateLimitBucket).where(RateLimitBucket.window_start < now() - timedelta(days=1)))
