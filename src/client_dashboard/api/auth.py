from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..auth.service import audit, create_session, now, revoke, revoke_all, token_hash
from ..models import AuthState, OAuthAttempt, User
from ..settings import get_settings
from .deps import get_db, require_authenticated_user, require_csrf

router = APIRouter(prefix="/api/auth")


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _cookie(data: dict) -> str:
    raw = base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode()).decode()
    signature = hmac.new(get_settings().session_secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return f"{raw}.{signature}"


def _read_cookie(value: str | None) -> dict | None:
    if not value or "." not in value:
        return None
    raw, signature = value.rsplit(".", 1)
    expected = hmac.new(get_settings().session_secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        data = json.loads(base64.urlsafe_b64decode(raw).decode())
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _limit(db: Session, request: Request, key: str, maximum: int, seconds: int) -> None:
    current = now()
    if seconds == 60:
        window = current.replace(second=0, microsecond=0)
    else:
        window = current.replace(minute=(current.minute // 10) * 10, second=0, microsecond=0)
    ip = request.client.host if request.client else "unknown"
    for attempt in range(3):
        try:
            result = db.execute(
                text("""
                    INSERT INTO rate_limit_buckets(route_key, client_ip, window_start, count)
                    VALUES (:route_key, :client_ip, :window_start, 1)
                    ON CONFLICT(route_key, client_ip, window_start)
                    DO UPDATE SET count = rate_limit_buckets.count + 1
                    RETURNING count
                """),
                {"route_key": key, "client_ip": ip, "window_start": window},
            ).scalar_one()
            db.commit()
            if result > maximum:
                raise HTTPException(status_code=429, detail="Too many requests", headers={"Retry-After": str(seconds)})
            return
        except HTTPException:
            raise
        except Exception as exc:
            db.rollback()
            if "locked" not in str(exc).lower() or attempt == 2:
                raise HTTPException(status_code=503, detail="Authentication service unavailable") from exc


def _clear_attempt(response: Response) -> None:
    response.delete_cookie("oauth_attempt", path="/api/auth/google")


def _set_flash(response: Response, category: str) -> None:
    response.set_cookie("auth_flash", _cookie({"category": category, "expires": (now() + timedelta(minutes=2)).timestamp()}), max_age=120, httponly=True, secure=get_settings().secure_cookies, samesite="lax", path="/api/auth")


@router.get("/google/login")
def google_login(request: Request, db: Session = Depends(get_db)):
    _limit(db, request, "login", 5, 600)
    settings = get_settings()
    attempt_id, state, nonce, verifier = (secrets.token_urlsafe(24) for _ in range(4))
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    db.add(OAuthAttempt(id=attempt_id, state_hash=token_hash(state), nonce_hash=token_hash(nonce), pkce_challenge=challenge, expires_at=now() + timedelta(minutes=10)))
    db.commit()
    query = urlencode({"client_id": settings.google_client_id, "redirect_uri": settings.callback_url, "response_type": "code", "scope": "openid email profile", "state": state, "nonce": nonce, "code_challenge": challenge, "code_challenge_method": "S256"})
    response = RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{query}", status_code=302)
    response.set_cookie("oauth_attempt", _cookie({"id": attempt_id, "nonce": nonce, "verifier": verifier}), max_age=600, httponly=True, secure=settings.secure_cookies, samesite="lax", path="/api/auth/google")
    return response


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    _limit(db, request, "callback", 10, 600)
    response = RedirectResponse("/admin/login", status_code=303)
    details = _read_cookie(request.cookies.get("oauth_attempt"))
    state = request.query_params.get("state")
    attempt = db.get(OAuthAttempt, details.get("id")) if details else None
    if not details or not state or not attempt or attempt.consumed_at or _utc(attempt.expires_at) <= now() or not hmac.compare_digest(attempt.state_hash, token_hash(state)) or not hmac.compare_digest(attempt.nonce_hash, token_hash(str(details.get("nonce", "")))):
        _set_flash(response, "failed")
        _clear_attempt(response)
        return response
    attempt.consumed_at = now()
    try:
        from authlib.integrations.httpx_client import AsyncOAuth2Client
        settings = get_settings()
        async with AsyncOAuth2Client(settings.google_client_id, settings.google_client_secret) as client:
            metadata_response = await client.request(
                "GET",
                "https://accounts.google.com/.well-known/openid-configuration",
                withhold_token=True,
            )
            metadata_response.raise_for_status()
            metadata = metadata_response.json()
            client.server_metadata = metadata
            await client.fetch_token(metadata["token_endpoint"], code=request.query_params.get("code", ""), redirect_uri=settings.callback_url, code_verifier=details["verifier"])
            userinfo_response = await client.get(metadata["userinfo_endpoint"])
            userinfo_response.raise_for_status()
            claims = userinfo_response.json()
    except Exception:
        audit(db, "login_rejected", "failed")
        db.commit()
        _set_flash(response, "failed")
        _clear_attempt(response)
        return response
    email = str(claims.get("email", "")).strip().casefold()
    subject = str(claims.get("sub", ""))
    state_row = db.get(AuthState, 1)
    user = db.query(User).first()
    if not claims.get("email_verified") or not subject:
        audit(db, "login_rejected", "denied")
        db.commit()
        _set_flash(response, "failed")
        _clear_attempt(response)
        return response
    if user is None and state_row and not state_row.bootstrap_completed and settings.bootstrap_enabled and email == settings.allowed_email:
        user = User(google_subject=subject, email=email, display_name=claims.get("name"))
        db.add(user)
        state_row.bootstrap_completed = True
    elif user is None or not user.active or user.email != email or user.google_subject != subject:
        audit(db, "login_rejected", "denied", user.id if user else None)
        db.commit()
        _set_flash(response, "unauthorized")
        _clear_attempt(response)
        return response
    # Bootstrap creates the user in this transaction; flush before using its
    # database-generated ID to create the first session.
    db.flush()
    token_value, _, _session = create_session(db, user)
    user.last_login_at = now()
    audit(db, "login_success", "ok", user.id)
    db.commit()
    response = RedirectResponse("/admin", status_code=303)
    response.set_cookie("session", token_value, max_age=86400, httponly=True, secure=settings.secure_cookies, samesite="lax", path="/")
    _clear_attempt(response)
    return response


@router.get("/flash")
def flash(request: Request, response: Response):
    data = _read_cookie(request.cookies.get("auth_flash")) or {}
    if data.get("expires", 0) < now().timestamp():
        data = {}
    response.delete_cookie("auth_flash", path="/api/auth")
    return {"category": data.get("category")} if data else {}


@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)):
    _limit(db, request, "me", 60, 60)
    user = require_authenticated_user(request, db)
    session = request.state.auth_session
    csrf = secrets.token_urlsafe(32)
    session.csrf_hash = token_hash(csrf)
    db.commit()
    return {"user": {"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role}, "csrf_token": csrf, "expires_at": _utc(session.expires_at)}


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db), user: User = Depends(require_csrf)):
    _limit(db, request, "logout", 10, 60)
    revoke(db, request.state.auth_session)
    audit(db, "logout", "ok", user.id)
    db.commit()
    result = Response(status_code=204)
    result.delete_cookie("session", path="/")
    return result


@router.post("/logout-all")
def logout_all(request: Request, db: Session = Depends(get_db), user: User = Depends(require_csrf)):
    _limit(db, request, "logout-all", 10, 60)
    revoke_all(db, user.id)
    audit(db, "all_sessions_revoked", "ok", user.id)
    db.commit()
    result = Response(status_code=204)
    result.delete_cookie("session", path="/")
    return result
