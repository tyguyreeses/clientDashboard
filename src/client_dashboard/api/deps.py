from __future__ import annotations

import hmac
from collections.abc import Generator
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..auth.service import token_hash
from ..database import SessionLocal
from ..models import AuthSession, User
from ..settings import get_settings


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_authenticated_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    session = db.query(AuthSession).filter(AuthSession.token_hash == token_hash(token)).first()
    expires_at = session.expires_at.replace(tzinfo=timezone.utc) if session and session.expires_at.tzinfo is None else (session.expires_at if session else None)
    if session is None or session.revoked_at is not None or expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    if not session.user.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    request.state.auth_session = session
    return session.user


def require_admin_user(user: User = Depends(require_authenticated_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return user


def require_csrf(request: Request, user: User = Depends(require_admin_user)) -> User:
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        settings = get_settings()
        origin = request.headers.get("origin")
        referer = request.headers.get("referer", "")
        if origin != settings.frontend_origin or (referer and not referer.startswith(settings.frontend_origin)):
            raise HTTPException(status_code=403, detail="Invalid request origin")
        session: AuthSession = request.state.auth_session
        csrf = request.headers.get("X-CSRF-Token", "")
        if not csrf or not hmac.compare_digest(token_hash(csrf), session.csrf_hash):
            raise HTTPException(status_code=403, detail="Invalid CSRF token")
    return user
