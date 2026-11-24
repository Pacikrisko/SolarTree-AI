"""Verify Google Identity Services credentials and bind them to SolarTree users."""
import os
from functools import partial

from fastapi import HTTPException
from google.auth import exceptions
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import GoogleIdentity, User
from .security import verify_password


def google_client_id():
    return os.getenv('GOOGLE_CLIENT_ID', '').strip()


def verified_claims(credential):
    audience = google_client_id()
    if not audience:
        raise HTTPException(503, 'Входът с Google още не е активиран.')
    try:
        claims = id_token.verify_oauth2_token(credential, partial(Request(), timeout=10), audience)
    except exceptions.TransportError:
        raise HTTPException(503, 'Google не отговори. Опитай отново.') from None
    except (ValueError, exceptions.GoogleAuthError):
        raise HTTPException(401, 'Входът с Google не бе потвърден. Опитай отново.') from None
    subject, email = claims.get('sub'), claims.get('email')
    if (not isinstance(subject, str) or not 1 <= len(subject) <= 255
            or claims.get('email_verified') is not True
            or not isinstance(email, str) or not 3 <= len(email) <= 200 or '@' not in email):
        raise HTTPException(403, 'Избери Google акаунт с потвърден имейл адрес.')
    return claims


def google_user(db: Session, claims: dict, password: str | None):
    """Return None only when the existing SolarTree account needs password confirmation."""
    subject = claims['sub']
    email = claims['email'].strip().lower()
    for attempt in range(2):
        identity = db.get(GoogleIdentity, subject)
        if identity:
            return db.get(User, identity.user_id)
        user = db.scalar(select(User).where(User.email == email).with_for_update())
        if user is not None:
            linked = db.scalar(select(GoogleIdentity).where(GoogleIdentity.user_id == user.id))
            if linked:
                if linked.subject == subject:
                    return user
                raise HTTPException(409, 'Профилът вече е свързан с друг Google акаунт.')
            if password is None:
                return None
            if not user.password_hash or not verify_password(password, user.password_hash):
                raise HTTPException(403, 'Настоящата парола е неправилна.')
        else:
            name = str(claims.get('name') or '').strip() or email.split('@')[0]
            # An empty hash denotes a Google-only account. Password login rejects it.
            user = User(email=email, name=name[:100], role='owner', password_hash='')
            db.add(user)
        try:
            db.flush()
            db.add(GoogleIdentity(subject=subject, user_id=user.id))
            db.commit()
            return user
        except IntegrityError:
            db.rollback()
            if attempt:
                raise HTTPException(409, 'Входът с Google не бе потвърден. Опитай отново.') from None
