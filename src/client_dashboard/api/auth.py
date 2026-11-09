from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..auth.service import audit, create_session, now, revoke, revoke_all, token_hash
from ..models import AuthState, OAuthAttempt, RateLimitBucket, User
from ..settings import get_settings
from .deps import get_db, require_authenticated_user, require_csrf

router = APIRouter(prefix="/api/auth")


def _cookie(data: dict) -> str:
    raw = base64.urlsafe_b64encode(json.dumps(data).encode()).decode()
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
        return json.loads(base64.urlsafe_b64decode(raw).decode())
    except Exception:
        return None


def _limit(db: Session, request: Request, key: str, maximum: int, seconds: int):
    current = now()
    window = current.replace(second=0, microsecond=0) if seconds == 60 else current.replace(minute=(current.minute // 10) * 10, second=0, microsecond=0)
    ip = request.client.host if request.client else "unknown"
    bucket = db.get(RateLimitBucket, (key, ip, window))
    if bucket is None:
        bucket = RateLimitBucket(route_key=key, client_ip=ip, window_start=window, count=0)
        db.add(bucket)
    bucket.count += 1
    if bucket.count > maximum:
        db.rollback()
        raise HTTPException(status_code=429, detail="Too many requests", headers={"Retry-After": str(seconds)})
    db.flush()


def _clear_attempt(response: Response):
    response.delete_cookie("oauth_attempt", path="/api/auth/google")


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
    response = RedirectResponse("/admin/login?error=failed", status_code=303)
    details = _read_cookie(request.cookies.get("oauth_attempt"))
    state = request.query_params.get("state")
    attempt = db.get(OAuthAttempt, details.get("id")) if details else None
    if not details or not state or not attempt or attempt.consumed_at or attempt.expires_at <= now() or not hmac.compare_digest(attempt.state_hash, token_hash(state)) or not hmac.compare_digest(attempt.nonce_hash, token_hash(details["nonce"])):
        _clear_attempt(response); return response
    attempt.consumed_at = now()
    # Authlib's validated OIDC client is intentionally used for code exchange and ID-token validation.
    try:
        from authlib.integrations.httpx_client import AsyncOAuth2Client
        settings = get_settings()
        async with AsyncOAuth2Client(settings.google_client_id, settings.google_client_secret) as client:
            token = await client.fetch_token("https://oauth2.googleapis.com/token", code=request.query_params["code"], redirect_uri=settings.callback_url, code_verifier=details["verifier"])
            claims = await client.parse_id_token(token, nonce=details["nonce"])
    except Exception:
        audit(db, "login_rejected", "failed"); db.commit(); _clear_attempt(response); return response
    email = str(claims.get("email", "")).strip().casefold()
    subject = str(claims.get("sub", ""))
    state_row = db.get(AuthState, 1)
    user = db.query(User).first()
    if not claims.get("email_verified") or not subject:
        audit(db, "login_rejected", "denied"); db.commit(); _clear_attempt(response); return response
    if user is None and state_row and not state_row.bootstrap_completed and settings.bootstrap_enabled and email == settings.allowed_email:
        user = User(google_subject=subject, email=email, display_name=claims.get("name"))
        db.add(user); state_row.bootstrap_completed = True
    elif user is None or not user.active or user.email != email or user.google_subject != subject:
        audit(db, "login_rejected", "denied", user.id if user else None); db.commit(); _clear_attempt(response); return response
    token_value, _, session = create_session(db, user)
    user.last_login_at = now(); audit(db, "login_success", "ok", user.id); db.commit()
    response = RedirectResponse("/admin", status_code=303)
    response.set_cookie("session", token_value, max_age=86400, httponly=True, secure=settings.secure_cookies, samesite="lax", path="/")
    _clear_attempt(response)
    return response


@router.get("/me")
def me(request: Request, db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    _limit(db, request, "me", 60, 60)
    session = request.state.auth_session
    csrf = secrets.token_urlsafe(32)
    session.csrf_hash = token_hash(csrf)
    db.commit()  # retain fixed expiry; no sliding renewal
    return {"user": {"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role}, "csrf_token": csrf, "expires_at": session.expires_at}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db), user: User = Depends(require_csrf)):
    _limit(db, request, "logout", 10, 60)
    revoke(db, request.state.auth_session); audit(db, "logout", "ok", user.id); db.commit(); response.delete_cookie("session", path="/"); return Response(status_code=204)


@router.post("/logout-all")
def logout_all(request: Request, response: Response, db: Session = Depends(get_db), user: User = Depends(require_csrf)):
    _limit(db, request, "logout-all", 10, 60)
    revoke_all(db, user.id); audit(db, "all_sessions_revoked", "ok", user.id); db.commit(); response.delete_cookie("session", path="/"); return Response(status_code=204)
