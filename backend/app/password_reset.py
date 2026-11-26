import logging
import os
import re
import secrets
import threading
import time
from collections import OrderedDict, deque
from datetime import timedelta
from hashlib import sha256
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session
from typing import Literal
from .database import SessionLocal, get_db
from .models import PasswordReset, User, utcnow
from .security import hash_password

router = APIRouter(prefix='/api/auth')
logger = logging.getLogger(__name__)
windows = OrderedDict()
lock = threading.Lock()


def limited(key, maximum):
    now = time.monotonic()
    with lock:
        times = windows.pop(key, deque())
        while times and times[0] <= now - 900:
            times.popleft()
        windows[key] = times
        if len(windows) > 8192:
            windows.popitem(last=False)
        if len(times) >= maximum:
            return True
        times.append(now)
        return False


def digest(value):
    return sha256(value.encode()).hexdigest()


class Forgot(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    language: Literal['bg','en'] = 'bg'


class Reset(BaseModel):
    token: str = Field(min_length=32, max_length=128)
    password: str = Field(min_length=8, max_length=128)


def issue_email(email, origin, language):
    with SessionLocal() as db:
        now = utcnow()
        db.execute(delete(PasswordReset).where(PasswordReset.expires_at <= now))
        user = db.scalar(select(User).where(User.email == email))
        if not user or not user.password_hash:
            db.commit()
            return
        token = secrets.token_urlsafe(32)
        db.add(PasswordReset(digest=digest(token), user_id=user.id, password_stamp=digest(user.password_hash),
                             expires_at=now + timedelta(minutes=30)))
        db.commit()
    url = f'{origin}/#/reset-password/{token}'
    subject, message = ('Solix password reset', 'Choose a new password within 30 minutes. If you did not request this, ignore this email.') if language == 'en' else ('Нова парола за Solix', 'Избери нова парола до 30 минути. Ако не си заявявал тази промяна, можеш да пренебрегнеш писмото.')
    try:
        response = httpx.post('https://api.resend.com/emails', timeout=10,
            headers={'Authorization':'Bearer ' + os.environ['RESEND_API_KEY']},
            json={'from':os.environ['PASSWORD_RESET_FROM'], 'to':[email], 'subject':subject, 'text':message+'\n\n'+url})
        response.raise_for_status()
    except httpx.HTTPError:
        logger.error('Password reset email delivery failed; check mail provider configuration.')


@router.post('/forgot-password',status_code=202)
def forgot_password(data: Forgot, request: Request, background: BackgroundTasks):
    origin = os.getenv('PASSWORD_RESET_ORIGIN') or os.getenv('PUBLIC_SCANNER_URL','')
    parsed = urlsplit(origin)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or
        parsed.query or parsed.fragment or parsed.path not in ('','/') or
        not os.getenv('RESEND_API_KEY') or not os.getenv('PASSWORD_RESET_FROM')):
        raise HTTPException(503,'Password recovery email is unavailable.')
    email = data.email.strip().lower()
    if not re.fullmatch(r'[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+',email):
        raise HTTPException(422,'Invalid email.')
    if not limited(('ip',request.client.host if request.client else ''),30) and not limited(('mail',digest(email)),3):
        background.add_task(issue_email,email,origin.rstrip('/'),data.language)
    return {'ok':True}


@router.post('/reset-password')
def reset_password(data: Reset, db: Session = Depends(get_db)):
    invalid = HTTPException(400,'Invalid or expired password reset link.')
    record = db.get(PasswordReset,digest(data.token))
    if not record or record.expires_at <= utcnow():
        raise invalid
    user = db.get(User,record.user_id)
    if not user or digest(user.password_hash) != record.password_stamp:
        raise invalid
    changed = db.execute(update(User).where(User.id==user.id, User.password_hash==user.password_hash)
        .values(password_hash=hash_password(data.password),session_version=User.session_version+1))
    if changed.rowcount != 1:
        db.rollback()
        raise invalid
    db.execute(delete(PasswordReset).where(PasswordReset.user_id==user.id))
    db.commit()
    return {'ok':True}
