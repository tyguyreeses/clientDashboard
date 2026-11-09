"""Initiate an operator-controlled Google identity replacement."""
from __future__ import annotations

import argparse
from datetime import timedelta

from sqlalchemy import select

from ..auth.service import audit, now, revoke_all
from ..database import SessionLocal
from ..models import AuthState, User


def initiate(current_email: str, replacement_email: str, confirmed: bool) -> None:
    if not confirmed:
        raise SystemExit("Explicit confirmation is required")
    current_email = current_email.strip().casefold()
    replacement_email = replacement_email.strip().casefold()
    if not replacement_email:
        raise SystemExit("Replacement email is required")
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == current_email))
        if user is None:
            raise SystemExit("Current admin email was not found")
        state = db.get(AuthState, 1)
        if state is None:
            raise SystemExit("Authentication state is not initialized")
        current = now()
        if state.pending_replacement_email and state.pending_replacement_expires_at:
            expires = state.pending_replacement_expires_at.replace(tzinfo=current.tzinfo) if state.pending_replacement_expires_at.tzinfo is None else state.pending_replacement_expires_at
            if expires > current:
                raise SystemExit("A live identity recovery already exists")
        state.pending_replacement_email = replacement_email
        state.pending_replacement_expires_at = current + timedelta(hours=24)
        state.recovery_started_at = current
        revoke_all(db, user.id)
        audit(db, "identity_recovery_initiated", "ok", user.id)
        db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Initiate a controlled Google identity recovery")
    parser.add_argument("--current-email", required=True)
    parser.add_argument("--replacement-email", required=True)
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    initiate(args.current_email, args.replacement_email, args.confirm)


if __name__ == "__main__":
    main()
