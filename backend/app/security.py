import os
import secrets
from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from fastapi import HTTPException, Header, status
from sqlalchemy.orm import Session
from .models import User

hasher = PasswordHasher()
# Generated per backend process when not set; suitable for local tests only.
SECRET_KEY = os.getenv('SECRET_KEY', '')
if not SECRET_KEY or SECRET_KEY.startswith('CHANGE_ME'):
    if os.getenv('APP_ENV', 'development').lower() == 'production':
        raise RuntimeError('Production requires a persistent SECRET_KEY environment variable.')
    SECRET_KEY = secrets.token_urlsafe(48)
ALGORITHM = 'HS256'

def hash_password(password: str) -> str:
    return hasher.hash(password)

def verify_password(password: str, encoded: str) -> bool:
    try:
        return hasher.verify(encoded, password)
    except (VerifyMismatchError, VerificationError):
        return False

def create_token(user: User) -> str:
    expiry = datetime.now(timezone.utc) + timedelta(hours=8)
    return jwt.encode({'sub': str(user.id), 'exp': expiry}, SECRET_KEY, algorithm=ALGORITHM)

def current_user(db: Session, authorization: str | None) -> User | None:
    if not authorization:
        return None
    if not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Невалиден тип удостоверяване.')
    token = authorization[7:]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = db.get(User, int(payload['sub']))
        if not user:
            raise ValueError('User no longer exists')
        return user
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise HTTPException(status_code=401, detail='Сесията е невалидна или изтекла.')

def require_user(user: User | None) -> User:
    if not user:
        raise HTTPException(status_code=401, detail='Влез в профила си, за да продължиш.')
    return user
