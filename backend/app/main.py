"""Solix API: account-scoped monitoring; advisory-only analytics and chat."""
import json
import os
from pathlib import Path
from uuid import UUID, uuid4
from math import sin, pi
from types import SimpleNamespace
from zoneinfo import ZoneInfo
import random
import logging
import base64
import io
import secrets
import qrcode
from urllib.parse import urlsplit
from datetime import timedelta
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from secrets import compare_digest
from hashlib import sha256
from typing import Annotated, Literal
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Depends, HTTPException, Header, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func, update, or_, delete
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from .database import Base, engine, get_db, SessionLocal
from PIL import Image, ImageOps
from .models import SupportFile, ChatRating, AccountPhoto, ChatConnection, LiveLease, SupportPresence, SupportAgent, DeviceWarranty, SupportTicket, SupportMessage
from .models import TreeMember, PairInvite, User, Tree, Reading, Alert, Maintenance, DeviceRegistration, MobilePairSession, DeviceSample, ChatExchange
from .seed import DEMO_MODE, seed_demo
from .google_login import google_client_id, google_user, verified_claims
from .password_reset import router as password_reset_router
from .security import hash_password, verify_password, create_token, current_user, require_user
from .locations import locate
from .ml import predict_power, detect_anomaly
from .maintenance import initialize_maintenance, maintenance_for, COMPONENTS
from .energy_outlook import energy_outlook
from .assistant import answer, account_report, assistant_provider, AssistantAPIError
from .monthly_archive import archive_months, monthly_archive
from .catalog import get_model, MODELS
from .resource_math import resource_estimate
from .urban_history import add_demo_urban_history, is_urban_simulator, urban_readings, urban_sample
from .migrations import upgrade
from .model_media import find_model_media, media_kind
from .mobile_scanner import scanner_page

def register_warranty(db, tree):
    if tree.kind=='archived' or db.get(DeviceWarranty,tree.code):
        return
    start=tree.created_at
    try:
        until=start.replace(year=start.year+10)
    except ValueError:  # February 29
        until=start.replace(year=start.year+10,day=28)
    db.add(DeviceWarranty(serial=tree.code,valid_until=until))


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    upgrade(engine)
    with SessionLocal() as db:
        seed_demo(db)
        ensure_printed_registrations(db)
        initialize_maintenance(db)
        for tree in db.scalars(select(Tree)):
            if tree.lat is None and tree.lng is None:
                tree.lat,tree.lng=locate(tree.location or '')
            register_warranty(db,tree)
        db.commit()
    yield

project_root = Path(__file__).resolve().parents[2]
release_manifest = project_root / 'frontend_dist/client-version.json'
if not release_manifest.is_file():
    release_manifest = project_root / 'frontend/public/client-version.json'
app_version = json.loads(release_manifest.read_text())['version']

app = FastAPI(title='Solix', version=app_version, lifespan=lifespan)
app.include_router(password_reset_router)
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],
                   allow_credentials=True,allow_methods=['*'],allow_headers=['*'])

class LoginIn(BaseModel):
    email: str
    password: str
class RegisterIn(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True,min_length=2,max_length=100)]
    email: str = Field(min_length=5,max_length=200)
    password: str = Field(min_length=8,max_length=128)
class TreeIn(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True,min_length=2,max_length=120)]
    code: str = Field(min_length=3,max_length=40,pattern=r'^[A-Za-z0-9-]+$')
    claim_token: str = Field(min_length=12,max_length=200)
    location: Annotated[str, StringConstraints(strip_whitespace=True,min_length=3,max_length=150)]
    lat: float | None = Field(default=None,ge=-90,le=90)
    lng: float | None = Field(default=None,ge=-180,le=180)
class ReadingIn(BaseModel):
    oxygen_flow_lph: float | None = Field(default=None,ge=0,le=100000)
    electrolyzer_power_w: float | None = Field(default=None,ge=0,le=200000)
    power_w: float = Field(ge=0,le=200000)
    temperature_c: float = Field(ge=-50,le=150)
    humidity_pct: float = Field(ge=0,le=100)
    h2_sensor_value: float = Field(ge=0,le=100000)
    water_pct: float = Field(ge=0,le=100)
class HistoryTurn(BaseModel):
    role: Literal['user','assistant']
    content: str = Field(min_length=1,max_length=1500)
class ChatIn(BaseModel):
    conversation_id: UUID | None = None
    require_existing: bool = False
    request_id: UUID | None = None
    language: Literal['bg','en'] = 'bg'
    message: str = Field(min_length=1,max_length=1600)
    tree_id: int | None = None
    report: Literal['overview','energy','maintenance'] | None = None
    history: list[HistoryTurn] = Field(default_factory=list,max_length=8)
class PairIn(BaseModel):
    code: str = Field(min_length=3,max_length=40)
    claim_token: str = Field(min_length=12,max_length=200)
class UpdateProfileIn(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True,min_length=2,max_length=100)]
class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8,max_length=128)

class ServiceScheduleIn(BaseModel):
    interval_days: int = Field(ge=1,le=3650)

class SimIn(BaseModel):
    mode: Literal['normal','anomaly']='normal'

def to_user(user: User):
    return {'id':user.id,'name':user.name,'email':user.email,'role':user.role,'is_admin':user.is_admin,'has_password':bool(user.password_hash)}
def to_reading(reading: Reading):
    return {'id':reading.id,'tree_id':reading.tree_id,'time':reading.time.isoformat()+'Z',
            'power_w':reading.power_w,'temperature_c':reading.temperature_c,
            'humidity_pct':reading.humidity_pct,'h2_sensor_value':reading.h2_sensor_value,
            'water_pct':reading.water_pct,'source':reading.source,
            'electrolyzer_power_w':reading.electrolyzer_power_w,
            'oxygen_flow_lph':reading.oxygen_flow_lph,'oxygen_basis':reading.oxygen_basis}
def prototype_estimates(when):
    local=when.replace(tzinfo=timezone.utc).astimezone(ZoneInfo('Europe/Sofia'))
    hour=local.hour+local.minute/60
    sun=max(0,sin(pi*(hour-6)/12)) if 6<hour<18 else 0
    power=round(16*sun,2)
    cell=round(.75*power,2)
    return dict(power_w=power,electrolyzer_power_w=cell,oxygen_flow_lph=round(.10*cell,2),
                water_pct=80,temperature_c=round(19+5*sun,1),humidity_pct=round(54-9*sun,1),
                h2_sensor_value=round(.10+.04*sun,3))


def prototype_history(db,tree,limit):
    end=datetime.now(timezone.utc).replace(tzinfo=None,second=0,microsecond=0)
    start=end-timedelta(minutes=15*(limit-1))
    buckets={}
    for cls in (Reading,DeviceSample):
        query=select(cls).where(cls.tree_id==tree.id,cls.time>=start,cls.time<end+timedelta(minutes=1))
        if cls is Reading: query=query.where(Reading.source=='device')
        for sample in db.scalars(query):
            slot=min(limit-1,int((sample.time-start).total_seconds()//900))
            buckets.setdefault(slot,[]).append(sample)
    rows=[]
    for slot in range(limit):
        when=start+timedelta(minutes=15*slot)
        values=prototype_estimates(when)
        measured=set()
        basis='simulation'
        for sample in sorted(buckets.get(slot,[]),key=lambda r:r.time):
            for field in values:
                value=getattr(sample,field,None)
                if value is not None:
                    values[field]=value
                    measured.add(field)
            if sample.oxygen_flow_lph is not None: basis=sample.oxygen_basis
            elif getattr(sample,'hydrogen_flow_lph',None) is not None:
                values['oxygen_flow_lph']=sample.hydrogen_flow_lph/2
                measured.add('oxygen_flow_lph')
                basis='estimated'
        if 'power_w' in measured and 'electrolyzer_power_w' not in measured:
            values['electrolyzer_power_w']=.75*max(0,min(16,values['power_w']))
        if 'oxygen_flow_lph' not in measured:
            values['oxygen_flow_lph']=round(.10*values['electrolyzer_power_w'],2)
        rows.append(SimpleNamespace(id=-int(when.replace(tzinfo=timezone.utc).timestamp()),tree_id=tree.id,time=when,
                    source='simulation' if len(measured)<len(values) else 'device',oxygen_basis=basis,**values))
    return rows


def recent_readings(db: Session, tree: Tree, limit: int, source: str | None = None):
    if is_urban_simulator(tree):
        return urban_readings(tree, limit) if source in (None, 'simulation') else []
    query = select(Reading).where(Reading.tree_id == tree.id)
    if source is not None:
        query = query.where(Reading.source == source)
    return db.scalars(query.order_by(desc(Reading.time)).limit(limit)).all()


def latest_reading(db: Session, tree: Tree):
    rows = recent_readings(db, tree, 1)
    return rows[0] if rows else None



def can_read(db,user: User, tree: Tree) -> bool:
    return (tree.owner_id==user.id or db.get(TreeMember,(tree.id,user.id)) is not None) and tree.kind==('municipal' if user.role=='municipality' else 'private')
def can_manage(db,user: User, tree: Tree) -> bool:
    # Joining with the persistent QR grants read-only access. Only the owner
    # can change coordinates, maintenance and device-wide alert state.
    return can_read(db,user,tree) and tree.owner_id == user.id

def accessible_trees(db: Session, user: User):
    kind = 'municipal' if user.role=='municipality' else 'private'
    return db.scalars(select(Tree).where(or_(Tree.owner_id==user.id,Tree.id.in_(select(TreeMember.tree_id).where(TreeMember.user_id==user.id))),Tree.kind==kind).order_by(Tree.id)).all()
def find_tree(db: Session, tree_id: int, user: User) -> Tree:
    tree = db.get(Tree,tree_id)
    # Return 404 rather than revealing existence of an unauthorized tree.
    if not tree or not can_read(db,user,tree):
        raise HTTPException(status_code=404,detail='Дървото не е намерено в твоя профил.')
    return tree

def to_tree(db: Session, tree: Tree, user_id: int | None = None):
    lat, lng = tree.lat, tree.lng
    if user_id is not None and user_id != tree.owner_id:
        member = db.get(TreeMember, (tree.id, user_id))
        if member and member.pin_lat is not None and member.pin_lng is not None:
            lat, lng = member.pin_lat, member.pin_lng
    now=datetime.now(timezone.utc).replace(tzinfo=None)
    operating = None
    sensor = None
    if is_urban_simulator(tree):
        last, operating = urban_sample(tree, now.replace(second=0, microsecond=0))
    else:
        last = latest_reading(db, tree)
        sensor = db.scalar(select(DeviceSample).where(DeviceSample.tree_id==tree.id).order_by(desc(DeviceSample.time)).limit(1))
    device_fresh=bool((last and last.source=='device' and (now-last.time).total_seconds()<900)
                   or (sensor and (now-sensor.time).total_seconds()<300))
    open_alerts=db.scalar(select(func.count()).select_from(Alert).where(Alert.tree_id==tree.id,Alert.acknowledged.is_(False))) or 0
    services=maintenance_for(db,tree)
    warranty=db.get(DeviceWarranty,tree.code)
    return {'prototype_estimates':{**prototype_estimates(now),'battery_pct':round(65+15*sin(2*pi*(now.hour-8)/24))} if tree.model_code=='ST-IVAN-P1' else None,'warranty_until':warranty.valid_until.date().isoformat() if warranty else None,'id':tree.id,'code':tree.code,'name':tree.name,'kind':tree.kind,
            'model':get_model(tree.model_code, tree.code),
            'location':tree.location,'lat':lat,'lng':lng,
            'latest':to_reading(last) if last else None,
            'simulation':operating, 'open_alerts':open_alerts,
            'media_kind': media_kind(tree.model_code),
            'service_attention':sum(s['status']!='ok' for s in services),
            'latest_sensors':({
              'time':sensor.time.isoformat()+'Z', 'temperature_c':sensor.temperature_c,
              'humidity_pct':sensor.humidity_pct,'mq8_adc_raw':sensor.mq8_adc_raw,
              'power_w':sensor.power_w,'water_pct':sensor.water_pct,
              'oxygen_flow_lph':sensor.oxygen_flow_lph if sensor.oxygen_flow_lph is not None else sensor.hydrogen_flow_lph/2 if sensor.hydrogen_flow_lph is not None else None} if sensor else None),
            'connection':'live' if device_fresh else 'model' if last and last.source=='simulation' else 'offline'}

def logged_in(db:Session=Depends(get_db),authorization:str|None=Header(default=None)):
    return require_user(current_user(db,authorization))

SHARED_QR_HASHES = {
    "IVAN-TREE-0001": "29dba20c596ad387522542bc2b14430fb09e3aba454b29744e4c50ca288e4d8f",
    "SOLIX-ARC-0001": "5be46454f15e90759b7c512e471af9767e959a440b05c0fa9697c972c8c2ef4e",
    "SOLIX-HALO-0002": "4b4b4bbfd00c14512dcaf4fbb6d8ddd7ab5e1920793657b888e58aa3cf76b85c"
}

# Permanent invitations printed in the original Solix pairing PDF.
PRINTED_QR_HASHES = {
    'IVAN-TREE-0001': '95b519437b72ead63f60dfb73d3cfad1dad781ba605a25e458ef491912e3028b',
    'SOLIX-ARC-0001': '24e42e41402eb5fd4499cd90375f1dd4c6766f63a81ce3898f34ddfc4fb19e27',
    'SOLIX-HALO-0002': '92beffc0e534187f6a26557924b8e8d61713e988de71508ec929f22fbad1e60d',
}


def ensure_printed_registrations(db: Session):
    for code, digest in PRINTED_QR_HASHES.items():
        reg = db.scalar(select(DeviceRegistration).where(DeviceRegistration.code == code))
        if reg is None:
            reg = DeviceRegistration(code=code, kind='private',
                model_code='ST-IVAN-P1' if code == 'IVAN-TREE-0001' else 'ST-URBAN-2KW',
                claim_hash=digest, telemetry_hash=secrets.token_hex(32))
            db.add(reg)
        if reg.claimed_tree_id is None:
            tree = db.scalar(select(Tree).where(Tree.code == code))
            if tree is not None:
                reg.claimed_tree_id = tree.id
                reg.bound_user_id = tree.owner_id


# Existing printed QR labels and the Prototype P1 manual must keep working.
# Only hashes are stored in code. The underlying QR token is never logged.
LEGACY_QR_ALIASES = {"URBAN-TREE-0001": "SOLIX-ARC-0001"}
LEGACY_QR_HASHES = {
    "IVAN-TREE-0001": "ec53ce14026b639d7e8f36dc5ef35ce273cf1b43a47aa97972bdc41af24d212c",
    "SOLIX-ARC-0001": "71cf3c6127b292e2007cc4e4fa564e1a31598ab9c4728f406ec3af46faec547f",
}


def is_permanent_invitation(code: str, digest: str) -> bool:
    return any(compare_digest(table.get(code, ''), digest)
               for table in (PRINTED_QR_HASHES, SHARED_QR_HASHES, LEGACY_QR_HASHES))


def verify_pair(db: Session, code: str, claim: str, user: User) -> DeviceRegistration:
    requested = code.strip().upper()
    canonical = LEGACY_QR_ALIASES.get(requested, requested)
    reg=db.scalar(select(DeviceRegistration).where(DeviceRegistration.code==canonical))
    # A QR verifies knowledge of the registration secret. An existing Tree
    # stays owned by its first owner; additional users join as members.
    digest = sha256(claim.encode()).hexdigest()
    invite = db.get(PairInvite,digest)
    if not reg or not (compare_digest(reg.claim_hash,digest)
                       or is_permanent_invitation(reg.code, digest)
                       or (invite and invite.registration_id==reg.id)):
        raise HTTPException(status_code=404,detail='Неуспешно сдвояване. Провери QR кода и кода за регистрация.')
    if reg.claimed_tree_id:
        tree = db.get(Tree, reg.claimed_tree_id)
        already_added = tree.owner_id == user.id or db.get(TreeMember, (tree.id, user.id))
        if already_added and not compare_digest(PRINTED_QR_HASHES.get(reg.code, ''), digest):
            raise HTTPException(409,'Дървото вече е добавено в профила.')
    elif reg.bound_user_id not in (None,user.id) and not is_permanent_invitation(reg.code, digest):
        raise HTTPException(status_code=409,detail='Това устройство вече е регистрирано.')
    if (user.role=='municipality' and reg.kind!='municipal') or (user.role=='owner' and reg.kind!='private'):
        raise HTTPException(status_code=403,detail='Устройството не принадлежи към този тип профил.')
    return reg

def attach_device(db: Session, reg: DeviceRegistration, user: User, tree: Tree, claim: str):
    db.execute(update(DeviceRegistration).where(DeviceRegistration.id==reg.id).values(code=reg.code))
    db.refresh(reg)
    verify_pair(db,reg.code,claim,user)
    db.execute(delete(PairInvite).where(PairInvite.registration_id==reg.id,PairInvite.digest==sha256(claim.encode()).hexdigest()))
    if reg.claimed_tree_id:
        existing = db.get(Tree, reg.claimed_tree_id)
        if existing.owner_id != user.id and not db.get(TreeMember, (existing.id, user.id)):
            db.add(TreeMember(tree_id=existing.id, user_id=user.id))
            db.flush()
        return existing
    # Reserve the inventory row before inserting a tree, even for simultaneous claims.
    reserved=db.execute(update(DeviceRegistration).where(
        DeviceRegistration.id==reg.id, DeviceRegistration.claimed_tree_id.is_(None),
        or_(DeviceRegistration.bound_user_id.is_(None),DeviceRegistration.bound_user_id==user.id,
            is_permanent_invitation(reg.code, sha256(claim.encode()).hexdigest()))
    ).values(bound_user_id=user.id))
    if reserved.rowcount!=1:
        raise HTTPException(status_code=409,detail='Това устройство вече е регистрирано.')
    if tree.lat is None and tree.lng is None:
        tree.lat,tree.lng=locate(tree.location or '')
    if tree.code == 'IVAN-TREE-0001' and tree.lat is None and tree.lng is None and tree.location in ('Добавено чрез QR','',None):
        tree.lat, tree.lng, tree.location = 42.4258, 25.6345, 'Stara Zagora'
    db.add(tree)
    db.flush()
    register_warranty(db,tree)
    reg.claimed_tree_id=tree.id
    return tree

@app.get('/api/health')
def health():
    provider=assistant_provider()
    return {'ok':True,'real_llm':bool(provider),'ai_provider':provider,'simulation_enabled':DEMO_MODE,
            'version':app_version}
class GoogleLoginIn(BaseModel):
    credential: str = Field(min_length=1, max_length=8192)
    password: str | None = Field(default=None, max_length=128)


@app.get('/api/auth/google/config')
def google_config():
    return {'client_id': google_client_id() or None}


@app.post('/api/auth/google')
def login_with_google(data:GoogleLoginIn, db:Session=Depends(get_db), x_requested_with:str|None=Header(default=None)):
    # GIS popup callback posts JSON. A cross-origin browser request with this
    # custom header requires approval by the application's CORS middleware.
    if x_requested_with != 'SolarTree':
        raise HTTPException(403, detail='Невалидна заявка за вход.')
    claims = verified_claims(data.credential)
    user = google_user(db, claims, data.password)
    if user is None:
        return {'requires_password': True, 'email': claims['email'].strip().lower()}
    return {'access_token': create_token(user), 'user': to_user(user)}


@app.post('/api/auth/login')
def login(data:LoginIn,db:Session=Depends(get_db)):
    user=db.scalar(select(User).where(User.email==data.email.strip().lower()))
    if not user or not user.password_hash or not verify_password(data.password,user.password_hash):
        raise HTTPException(status_code=401,detail='Невалиден имейл или парола.')
    return {'access_token':create_token(user),'user':to_user(user)}
@app.post('/api/auth/register',status_code=201)
def register(data:RegisterIn,db:Session=Depends(get_db)):
    email=data.email.strip().lower()
    if '@' not in email or '.' not in email.split('@')[-1]:
        raise HTTPException(status_code=422,detail='Невалиден имейл адрес.')
    try:
        if db.scalar(select(User).where(User.email==email)):
            raise HTTPException(status_code=409,detail='Този имейл вече е регистриран.')
        user=User(name=data.name.strip(),email=email,password_hash=hash_password(data.password),role='owner')
        db.add(user)
        db.commit()
        db.refresh(user)
        return {'access_token':create_token(user),'user':to_user(user)}
    except HTTPException:
        raise
    except IntegrityError:
        db.rollback()
        logging.exception('Solix registration integrity error')
        raise HTTPException(status_code=409,detail='Този имейл вече е регистриран. Опитай Вход.') from None
    except OperationalError as exc:
        db.rollback()
        logging.exception('SolarTree registration database operational error')
        msg=str(getattr(exc,'orig',exc)).lower()
        if 'locked' in msg or 'busy' in msg:
            detail='Базата данни е заета. Затвори останалите FastAPI прозорци и опитай пак.'
        elif 'readonly' in msg or 'read-only' in msg:
            detail='Базата данни е само за четене. Провери правата на папката backend.'
        else:
            detail='Проблем с връзката към базата данни. Виж грешката в терминала на FastAPI.'
        raise HTTPException(status_code=503,detail=detail) from None
    except SQLAlchemyError:
        db.rollback()
        logging.exception('SolarTree registration SQLAlchemy error')
        raise HTTPException(status_code=500,detail='Грешка при запис в базата данни. Виж терминала на FastAPI.') from None
    except Exception:
        db.rollback()
        logging.exception('SolarTree registration unexpected error')
        raise HTTPException(status_code=500,detail='Неуспешно създаване на профил. Виж терминала на FastAPI за подробности.') from None
def require_admin(user: User = Depends(logged_in)):
    if not user.is_admin:
        raise HTTPException(403, 'Изисква се администраторски достъп.')
    return user


@app.get('/api/admin/devices')
def admin_devices(offset: int = Query(0, ge=0), db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    latest_sample = select(func.max(DeviceSample.time)).where(
        DeviceSample.tree_id == DeviceRegistration.claimed_tree_id
    ).correlate(DeviceRegistration).scalar_subquery()
    rows = db.execute(select(DeviceRegistration, latest_sample).order_by(
        DeviceRegistration.id.desc()).limit(51).offset(offset)).all()
    return {'has_more': len(rows) > 50, 'devices': [
        {'code': reg.code, 'model': reg.model_code,
         'status': 'active' if reg.claimed_tree_id else 'reserved' if reg.bound_user_id else 'free',
         'sample_time': stamp.isoformat() + 'Z' if stamp else None}
        for reg, stamp in rows[:50]
    ]}


@app.post('/api/admin/simulators', status_code=201)
def admin_simulator(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    code = 'URBAN-SIM-' + secrets.token_hex(8).upper()
    claim = secrets.token_urlsafe(32)
    telemetry = secrets.token_urlsafe(40)
    payload = f'STREE1|{code}|{claim}'
    png = io.BytesIO()
    qrcode.make(payload).save(png, format='PNG')
    db.add(DeviceRegistration(code=code, model_code='ST-URBAN-2KW', kind='private',
           claim_hash=sha256(claim.encode()).hexdigest(), telemetry_hash=sha256(telemetry.encode()).hexdigest()))
    db.commit()
    from fastapi.responses import JSONResponse
    return JSONResponse({'code': code, 'claim': claim, 'telemetry': telemetry,
                         'qr': 'data:image/png;base64,' + base64.b64encode(png.getvalue()).decode()},
                        status_code=201, headers={'Cache-Control': 'no-store'})


@app.get('/api/auth/me')
def me(user:User=Depends(logged_in)):
    return to_user(user)

@app.patch('/api/auth/me')
def update_profile(data:UpdateProfileIn,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    user.name=data.name.strip()
    db.commit();db.refresh(user)
    return to_user(user)

@app.post('/api/auth/change-password')
def change_password(data:ChangePasswordIn,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    if not user.password_hash or not verify_password(data.current_password,user.password_hash):
        raise HTTPException(status_code=403,detail='Настоящата парола е неправилна.')
    user.password_hash=hash_password(data.new_password)
    db.commit()
    return {'ok':True}

@app.post('/api/pair/resolve')
def pair_resolve(data:PairIn,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    reg=verify_pair(db,data.code,data.claim_token,user)
    return {'code':reg.code,'model':get_model(reg.model_code, reg.code),'kind':reg.kind}

class ScanIn(BaseModel):
    payload: str = Field(min_length=15,max_length=1000)

class SensorIn(BaseModel):
    hydrogen_flow_lph: float | None = Field(default=None,ge=0,le=200000)
    temperature_c: float | None = Field(default=None,ge=-50,le=150)
    humidity_pct: float | None = Field(default=None,ge=0,le=100)
    mq8_adc_raw: int | None = Field(default=None,ge=0,le=65535)
    power_w: float | None = Field(default=None,ge=0,le=200000)
    water_pct: float | None = Field(default=None,ge=0,le=100)
    oxygen_flow_lph: float | None = Field(default=None,ge=0,le=100000)

@app.post('/api/pair-sessions')
def create_pair_session(language:Literal['bg','en']='bg',db:Session=Depends(get_db),user:User=Depends(logged_in)):
    token=secrets.token_urlsafe(32)
    expiry=datetime.now(timezone.utc).replace(tzinfo=None)+timedelta(minutes=5)
    session=MobilePairSession(user_id=user.id,token_hash=sha256(token.encode()).hexdigest(),expires_at=expiry)
    db.add(session);db.commit();db.refresh(session)
    origin=os.getenv('PUBLIC_SCANNER_URL','').strip().rstrip('/')
    # The phone's camera needs a secure origin; HTTP localhost on the PC is not reachable.
    url=f'{origin}/scan/{token}' if origin.startswith('https://') else None
    image=None
    if url:
        if language=='en':
            url+='?lang=en'
        buffer=io.BytesIO()
        qrcode.make(url).save(buffer,format='PNG')
        image='data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode()
    return {'id':session.id,'url':url,'qr_data_uri':image,'expires_at':expiry.isoformat()+'Z',
            'needs_https':url is None}

@app.get('/api/pair-sessions/{session_id}')
def pair_session_status(session_id:int,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    session=db.get(MobilePairSession,session_id)
    if not session or session.user_id!=user.id:
        raise HTTPException(status_code=404,detail='Сесията не е намерена.')
    if session.status=='pending' and session.expires_at<datetime.now(timezone.utc).replace(tzinfo=None):
        session.status='expired';db.commit()
    tree=db.get(Tree,session.tree_id) if session.status=='completed' and session.tree_id else None
    return {'status':session.status,'tree_id':tree.id if tree else None,
            'tree_name':tree.name if tree else None,'model':get_model(tree.model_code, tree.code)['name'] if tree else None}

def mobile_session(db:Session,token:str)->MobilePairSession:
    if len(token)>128 or len(token)<32:
        raise HTTPException(status_code=404,detail='Сесията не е намерена.')
    row=db.scalar(select(MobilePairSession).where(MobilePairSession.token_hash==sha256(token.encode()).hexdigest()))
    if not row:
        raise HTTPException(status_code=404,detail='Сесията не е намерена.')
    if row.expires_at<datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(status_code=410,detail='Линкът е изтекъл. Създай нов от компютъра.')
    return row

@app.get('/scan/{token}')
def phone_scanner(token:str,lang:Literal['bg','en']='bg',db:Session=Depends(get_db)):
    session=mobile_session(db,token)
    if session.status!='pending':
        raise HTTPException(status_code=410,detail='Сесията вече е използвана.')
    return scanner_page(lang)

@app.post('/api/scan/{token}')
def phone_scan(token:str,data:ScanIn,db:Session=Depends(get_db)):
    session=mobile_session(db,token)
    if session.status!='pending':
        raise HTTPException(status_code=409,detail='Сесията вече е приключила.')
    if session.attempts>=6:
        raise HTTPException(status_code=429,detail='Твърде много неуспешни опити.')
    payload=data.payload.strip()
    code=claim=''
    if payload.startswith('STREE1|'):
        fields=payload.split('|')
        if len(fields)==3: _,code,claim=fields
    else:
        u=urlsplit(payload)
        if u.scheme=='solartree' or (u.scheme=='https' and u.path.endswith('/pair')):
            from urllib.parse import parse_qs
            params=parse_qs(u.query)
            code=(params.get('device') or [''])[0]
            claim=(params.get('claim') or [''])[0]
    user=db.get(User,session.user_id)
    try:
        if not user or not code or not claim:
            raise HTTPException(status_code=422,detail='Невалиден регистрационен QR код.')
        reg=verify_pair(db,code,claim,user)
    except HTTPException:
        session.attempts+=1;db.commit()
        raise
    tree=Tree(code=reg.code,model_code=reg.model_code,kind=reg.kind,owner_id=user.id,
              name=get_model(reg.model_code, reg.code)['name'],location='Добавено чрез QR')
    candidate=tree
    tree=attach_device(db,reg,user,tree,claim)
    session.status='completed';session.tree_id=tree.id
    if DEMO_MODE and candidate is tree and not is_urban_simulator(tree): add_demo_urban_history(db,tree)
    db.commit();initialize_maintenance(db)
    return {'ok':True,'name':tree.name,'model':get_model(tree.model_code, tree.code)['name']}

@app.get('/api/trees/{tree_id}/resources')
def resources(tree_id: int, water_fill_pct: float = Query(default=100.0, ge=0, le=100),
              pressure_bar_g: float | None = Query(default=None, ge=0, le=500),
              fuel_cell_load_kw: float | None = Query(default=None, ge=0),
              efficiency: float = Query(default=0.50, gt=0, le=1),
              db: Session = Depends(get_db), user: User = Depends(logged_in)):
    tree = find_tree(db, tree_id, user)
    model = get_model(tree.model_code, tree.code)
    if not model.get('water_tank_l') or not model.get('hydrogen_tank_l'):
        raise HTTPException(status_code=404, detail='За този модел няма данни за резервоарите.')
    if is_urban_simulator(tree):
        reading, operating = urban_sample(tree, datetime.now(timezone.utc).replace(tzinfo=None))
        water_fill_pct = reading.water_pct
        pressure_bar_g = operating['hydrogen_pressure_bar_g']
        fuel_cell_load_kw = operating['fuel_cell_load_kw']
        efficiency = .5
    try:
        return resource_estimate(water_capacity_l=model['water_tank_l'],
            hydrogen_tank_internal_l=model['hydrogen_tank_l'],
            oxygen_nominal_nlph=model['oxygen_nominal_lph'],
            fuel_cell_power_kw=model['fuel_cell_kw'],
            water_fill_pct=water_fill_pct, pressure_bar_g=pressure_bar_g,
            fuel_cell_load_kw=fuel_cell_load_kw, fuel_cell_efficiency=efficiency)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.get('/api/trees')
def trees(db:Session=Depends(get_db),user:User=Depends(logged_in)):
    return [to_tree(db,t,user.id) for t in accessible_trees(db,user)]
@app.post('/api/trees',status_code=201)
def create_tree(data:TreeIn,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    # Keep one Tree per serial; subsequent valid QR scans link a new account to it.
    reg=verify_pair(db,data.code,data.claim_token,user)
    if reg.claimed_tree_id is None and db.scalar(select(Tree).where(Tree.code==reg.code)):
        raise HTTPException(status_code=409,detail='Това устройство вече е регистрирано.')
    tree=Tree(name=data.name.strip(),code=reg.code,model_code=reg.model_code,kind=reg.kind,
              location=data.location.strip(),owner_id=user.id,
              lat=data.lat,lng=data.lng)
    candidate=tree
    tree=attach_device(db,reg,user,tree,data.claim_token)
    if DEMO_MODE and candidate is tree and not is_urban_simulator(tree): add_demo_urban_history(db,tree)
    db.commit();db.refresh(tree)
    initialize_maintenance(db)
    return to_tree(db,tree,user.id)
class CoordinatesIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


@app.patch('/api/trees/{tree_id}/coordinates')
def set_coordinates(tree_id:int, data:CoordinatesIn, db:Session=Depends(get_db), user:User=Depends(logged_in)):
    tree=find_tree(db,tree_id,user)
    if tree.owner_id == user.id:
        tree.lat, tree.lng = data.lat, data.lng
    else:
        member = db.get(TreeMember, (tree.id, user.id))
        member.pin_lat, member.pin_lng = data.lat, data.lng
    db.commit()
    return {'ok':True}


@app.delete('/api/trees/{tree_id}')
def remove_tree(tree_id:int,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    db.scalar(select(DeviceRegistration).where(DeviceRegistration.claimed_tree_id==tree_id).with_for_update())
    tree=db.scalar(select(Tree).where(Tree.id==tree_id).with_for_update())
    if tree is None or not can_read(db,user,tree):
        raise HTTPException(status_code=404,detail='Дървото не е намерено в твоя профил.')
    registration=db.scalar(select(DeviceRegistration).where(DeviceRegistration.claimed_tree_id==tree.id))
    member=db.get(TreeMember,(tree.id,user.id))
    if member:
        db.delete(member)
        db.commit()
        return {'ok':True}
    successor=db.scalar(select(TreeMember).where(TreeMember.tree_id==tree.id).order_by(TreeMember.user_id))
    if successor and registration:
        tree.owner_id=registration.bound_user_id=successor.user_id
        db.delete(successor)
        db.commit()
        return {'ok':True}
    if registration:
        registration.bound_user_id=user.id
        registration.claimed_tree_id=None
    # Keep historical records on an inaccessible installation. A new pairing
    # gets its own ID and history, including when the same owner pairs again.
    tree.code=f'archived:{tree.id}'
    tree.kind='archived'
    tree.owner_id=None
    db.commit()
    return {'ok':True}

@app.get('/api/trees/{tree_id}/monthly-archive')
def tree_archive(tree_id:int,month:str|None=None,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    tree=find_tree(db,tree_id,user)
    months=archive_months()
    if month is not None and month not in months:
        raise HTTPException(422,'Избери месец от наличния архив.')
    return {**monthly_archive(tree,month or months[0]),'months':months}


@app.get('/api/trees/{tree_id}')
def tree_detail(tree_id:int,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    return to_tree(db,find_tree(db,tree_id,user),user.id)
@app.get('/api/trees/{tree_id}/config')
def get_tree_config(tree_id:int,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    tree=find_tree(db,tree_id,user)
    return {'tree_id':tree.id,**get_model(tree.model_code, tree.code)}

@app.get('/api/trees/{tree_id}/media')
def get_tree_media(tree_id:int,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    tree=find_tree(db,tree_id,user)
    path,mime=find_model_media(tree.model_code)
    return FileResponse(path,media_type=mime,headers={
        'Cache-Control':'private, max-age=600','X-Content-Type-Options':'nosniff'})

# Personal media changes are intentionally disabled. Photos/videos belong to the
# manufacturer/service catalogue, not the end-user's device record.
@app.post('/api/trees/{tree_id}/media')
@app.delete('/api/trees/{tree_id}/media')
def locked_tree_media(tree_id:int,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    find_tree(db,tree_id,user)
    raise HTTPException(status_code=403,detail='Изображенията се задават само сервизно за официалния модел.')

@app.get('/api/trees/{tree_id}/readings')
def tree_readings(tree_id:int,limit:int=120,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    tree=find_tree(db,tree_id,user)
    limit=max(1,min(limit,500))
    if tree.model_code=="ST-IVAN-P1": return [to_reading(r) for r in prototype_history(db,tree,limit)]
    rows=recent_readings(db,tree,limit)
    return [to_reading(r) for r in reversed(rows)]
@app.get('/api/trees/{tree_id}/oxygen')
def tree_oxygen(tree_id:int,limit:int=240,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    tree=find_tree(db,tree_id,user)
    last=latest_reading(db,tree)
    # Keep virtual history and device telemetry separate; never report a mixed total as measured.
    limit=max(2,min(limit,500))
    if tree.model_code=='ST-IVAN-P1':
        rows=prototype_history(db,tree,limit)
    elif last is None:
        return {'tree_id':tree.id,'points':[],'total_l':0,'current_flow_lph':None,'basis':'unavailable','note':'Няма налични измервания.'}
    else:
        rows=sorted(recent_readings(db,tree,limit,last.source),key=lambda r:r.time)
    points=[]; total=0.0; prev=None
    for r in rows:
        flow=r.oxygen_flow_lph
        if flow is None and isinstance(r,DeviceSample) and r.hydrogen_flow_lph is not None:
            flow=r.hydrogen_flow_lph/2
        if flow is None:
            prev=None
            continue
        if prev is not None:
            delta=(r.time-prev[0]).total_seconds()/3600
            if 0<delta<=.5:
                total+=(prev[1]+flow)/2 * delta
        points.append({'time':r.time.isoformat()+'Z','oxygen_flow_lph':round(flow,2),
                       'cumulative_l':round(total,2),'basis':r.oxygen_basis,'source':getattr(r,'source','device')})
        prev=(r.time,flow)
    return {'tree_id':tree.id,'points':points,'total_l':round(total,2),
            'current_flow_lph':round(points[-1]['oxygen_flow_lph'],2) if points else None,
            'basis':points[-1]['basis'] if points else 'unavailable',
            'note':'За липсващите показания се използва моделна оценка.' if tree.model_code=='ST-IVAN-P1' else 'Натрупаният обем е изчислен от симулирания дебит за показания период.' if is_urban_simulator(tree) else 'Обемът е изчислен от наличните измервания за показания период; празните интервали не се запълват.'}

@app.get('/api/trees/{tree_id}/forecast')
def tree_forecast(tree_id:int,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    tree=find_tree(db,tree_id,user)
    latest=latest_reading(db,tree)
    if tree.model_code=='ST-IVAN-P1': return predict_power(prototype_history(db,tree,120))
    if latest is None:
        return predict_power([])
    rows=recent_readings(db,tree,120,latest.source)
    return predict_power(list(reversed(rows)))
@app.get('/api/trees/{tree_id}/maintenance')
def tree_maintenance(tree_id:int,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    return maintenance_for(db,find_tree(db,tree_id,user))
@app.get('/api/maintenance')
def all_maintenance(db:Session=Depends(get_db),user:User=Depends(logged_in)):
    return [service for t in accessible_trees(db,user) for service in maintenance_for(db,t)]
@app.post('/api/trees/{tree_id}/maintenance/{component}/complete')
def service_complete(tree_id:int,component:str,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    tree=find_tree(db,tree_id,user)
    if not can_manage(db,user,tree) or component not in COMPONENTS:
        raise HTTPException(status_code=404,detail='Непознат сервизен компонент.')
    record=db.scalar(select(Maintenance).where(Maintenance.tree_id==tree.id,Maintenance.component==component))
    if not record:
        raise HTTPException(status_code=404,detail='Няма сервизен запис.')
    record.last_serviced_at=datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return {'ok':True,'maintenance':maintenance_for(db,tree)}

@app.put('/api/trees/{tree_id}/maintenance/{component}')
def update_service_schedule(tree_id:int,component:str,data:ServiceScheduleIn,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    tree=find_tree(db,tree_id,user)
    if not can_manage(db,user,tree):
        raise HTTPException(status_code=403,detail='Само собственикът може да променя сервизния график.')
    if component not in COMPONENTS:
        raise HTTPException(status_code=404,detail='Непознат сервизен компонент.')
    record=db.scalar(select(Maintenance).where(Maintenance.tree_id==tree.id,Maintenance.component==component))
    if not record:
        raise HTTPException(status_code=404,detail='Няма сервизен запис.')
    record.interval_days=data.interval_days
    db.commit()
    return {'ok':True,'maintenance':maintenance_for(db,tree)}

@app.get('/api/alerts')
def alerts(db:Session=Depends(get_db),user:User=Depends(logged_in)):
    permitted_ids={t.id for t in accessible_trees(db,user)}
    rows=db.scalars(select(Alert).order_by(desc(Alert.id)).limit(250)).all()
    out=[]
    for a in rows:
        if a.tree_id in permitted_ids:
            t=db.get(Tree,a.tree_id)
            out.append({'id':a.id,'tree_id':a.tree_id,'tree_name':t.name,'message':a.message,
                        'severity':a.severity,'acknowledged':a.acknowledged,
                        'time':a.created_at.isoformat()+'Z','can_ack':t.owner_id==user.id})
    return out
@app.post('/api/alerts/{alert_id}/ack')
def acknowledge(alert_id:int,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    a=db.get(Alert,alert_id)
    if not a:
        raise HTTPException(status_code=404,detail='Няма такова известие.')
    tree=find_tree(db,a.tree_id,user)
    if not can_manage(db,user,tree):
        raise HTTPException(status_code=403,detail='Само собственикът може да потвърждава общите известия.')
    a.acknowledged=True;db.commit()
    return {'ok':True}

# Data ingestion is not control: this endpoint only stores telemetry.
def save_reading(db:Session,tree:Tree,metrics:ReadingIn,source:str):
    history=db.scalars(select(Reading).where(Reading.tree_id==tree.id).order_by(desc(Reading.time)).limit(100)).all()
    oxy_basis='simulation' if source=='simulation' and metrics.oxygen_flow_lph is not None else ('measured' if source=='device' and metrics.oxygen_flow_lph is not None else 'unavailable')
    new=Reading(tree_id=tree.id,time=datetime.now(timezone.utc).replace(tzinfo=None),source=source,
                oxygen_basis=oxy_basis,**metrics.model_dump())
    anomalous,score=detect_anomaly(list(reversed(history)),new)
    db.add(new)
    if anomalous:
        db.add(Alert(tree_id=tree.id,message='Необичайни стойности в телеметрията. Необходима е проверка.',severity='warning'))
    db.commit();db.refresh(new)
    return {'reading':to_reading(new),'anomaly':anomalous,'anomaly_score':score}
@app.post('/api/trees/{tree_id}/simulate')
def simulate(tree_id:int,data:SimIn,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    if not DEMO_MODE:
        raise HTTPException(status_code=403,detail='Режимът за сценарии е изключен.')
    tree=find_tree(db,tree_id,user)
    if is_urban_simulator(tree):
        raise HTTPException(status_code=409,detail='Това тестово устройство има автоматична симулация.')
    if data.mode=='anomaly':
        metrics=ReadingIn(power_w=0,temperature_c=68,humidity_pct=10,h2_sensor_value=6.7,water_pct=2,
                          oxygen_flow_lph=0,electrolyzer_power_w=0)
    else:
        import math
        now=datetime.now(timezone.utc)
        sun=max(0,math.sin(math.pi*(now.hour+now.minute/60-6)/13)) if 6<=now.hour<=19 else 0
        old=latest_reading(db,tree)
        metrics=ReadingIn(power_w=round(max(0,sun*1300+random.uniform(-40,40)),1),
                temperature_c=round(20+sun*8,1),humidity_pct=round(51-13*sun,1),
                h2_sensor_value=0.1,water_pct=max(0,round((old.water_pct if old else 85)-.1,1)),
                oxygen_flow_lph=round(max(0,sun*1300)*.065,1),electrolyzer_power_w=round(max(0,sun*1300)*.65,1))
    res=save_reading(db,tree,metrics,'simulation')
    if data.mode=='anomaly' and not res['anomaly']:
        db.add(Alert(tree_id=tree.id,message='Отклонение в тестов сценарий. Проверете стойностите.',severity='warning'))
        db.commit();res['anomaly']=True
    return res
@app.post('/api/device/{code}/sensors')
def device_sensors(code:str,metrics:SensorIn,db:Session=Depends(get_db),x_device_key:str|None=Header(default=None)):
    """Partial genuine Pico measurements: do not invent absent power/oxygen/water sensors."""
    tree=db.scalar(select(Tree).where(Tree.code==code.upper()))
    if not tree: raise HTTPException(status_code=404,detail='Непознато устройство.')
    reg=db.scalar(select(DeviceRegistration).where(DeviceRegistration.code==tree.code))
    digest=sha256((x_device_key or '').encode()).hexdigest()
    if not(reg and x_device_key and compare_digest(reg.telemetry_hash,digest) and reg.claimed_tree_id==tree.id):
        raise HTTPException(status_code=401,detail='Устройството не е удостоверено.')
    if is_urban_simulator(tree):
        raise HTTPException(status_code=409,detail='Този сериен номер е за виртуално устройство.')
    if not any(v is not None for v in metrics.model_dump().values()):
        raise HTTPException(status_code=422,detail='Липсват измервания от датчици.')
    sample=DeviceSample(tree_id=tree.id,**metrics.model_dump())
    db.add(sample);db.commit()
    return {'ok':True,'time':sample.time.isoformat()+'Z'}

@app.post('/api/device/{code}/reading')
def device_ingest(code:str,metrics:ReadingIn,db:Session=Depends(get_db),x_device_key:str|None=Header(default=None)):
    tree=db.scalar(select(Tree).where(Tree.code==code.upper()))
    if not tree:
        raise HTTPException(status_code=404,detail='Непознато устройство.')
    reg=db.scalar(select(DeviceRegistration).where(DeviceRegistration.code==tree.code))
    key_digest=sha256((x_device_key or '').encode()).hexdigest()
    per_device_ok=bool(reg and x_device_key and compare_digest(reg.telemetry_hash,key_digest)
                       and reg.claimed_tree_id==tree.id)
    # Compatibility for a LOCAL prototype only; shared keys must not be deployed for a fleet.
    legacy=os.getenv('DEVICE_API_TOKEN','')
    legacy_ok=bool(DEMO_MODE and legacy and x_device_key and compare_digest(legacy,x_device_key))
    if not (per_device_ok or legacy_ok):
        raise HTTPException(status_code=401,detail='Устройството не е удостоверено.')
    if is_urban_simulator(tree):
        raise HTTPException(status_code=409,detail='Този сериен номер е за виртуалния Solix Arc 2K.')
    return save_reading(db,tree,metrics,'device')
def thread_filters(user_id, tree_id, conversation_id):
    return (ChatExchange.user_id == user_id, ChatExchange.tree_id == tree_id,
            ChatExchange.conversation_id == (str(conversation_id) if conversation_id else None))

def lock_chat_owner(db, user_id):
    db.execute(select(User.id).where(User.id == user_id).with_for_update()).one()

@app.get('/api/chat/conversations')
def conversations(db: Session = Depends(get_db), user: User = Depends(logged_in)):
    tree_ids = [tree.id for tree in accessible_trees(db, user)]
    groups = (select(func.min(ChatExchange.id).label('first_id'), func.max(ChatExchange.id).label('last_id'))
              .where(ChatExchange.user_id == user.id,
                     or_(ChatExchange.tree_id.is_(None), ChatExchange.tree_id.in_(tree_ids)))
              .group_by(ChatExchange.tree_id, ChatExchange.conversation_id).subquery())
    rows = db.execute(select(ChatExchange.tree_id, ChatExchange.conversation_id, ChatExchange.question)
                      .join(groups, ChatExchange.id == groups.c.first_id)
                      .order_by(groups.c.last_id.desc()))
    return [{'conversation_id': row.conversation_id, 'tree_id': row.tree_id, 'title': row.question[:100]} for row in rows]

@app.delete('/api/chat/conversations')
def clear_conversations(db: Session = Depends(get_db), user: User = Depends(logged_in)):
    lock_chat_owner(db, user.id)
    db.execute(delete(ChatExchange).where(ChatExchange.user_id == user.id))
    db.commit()
    return {'ok': True}

@app.delete('/api/chat/conversations/selected')
def delete_conversation(tree_id: int | None = None, conversation_id: UUID | None = None,
                        db: Session = Depends(get_db), user: User = Depends(logged_in)):
    lock_chat_owner(db, user.id)
    db.execute(delete(ChatExchange).where(*thread_filters(user.id, tree_id, conversation_id)))
    db.commit()
    return {'ok': True}

def exchange_json(row):
    return {'id':row.id,'question':row.question,'reply':row.reply,'mode':row.mode,'model':row.model,
            'tree_id':row.tree_id,'created_at':row.created_at.isoformat()+'Z'}

@app.get('/api/chat/history')
def chat_history(tree_id:int|None=None,conversation_id:UUID|None=None,before:int|None=Query(None,gt=0),
                 db:Session=Depends(get_db),user:User=Depends(logged_in)):
    if tree_id is not None:
        find_tree(db,tree_id,user)
    query=select(ChatExchange).where(*thread_filters(user.id,tree_id,conversation_id))
    if before is not None:
        query=query.where(ChatExchange.id<before)
    rows=db.scalars(query.order_by(desc(ChatExchange.id)).limit(31)).all()
    return {'exchanges':[exchange_json(row) for row in reversed(rows[:30])],'has_more':len(rows)>30}

@app.post('/api/chat')
def chat(data:ChatIn,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    focus=find_tree(db,data.tree_id,user) if data.tree_id is not None else None
    request_id=str(data.request_id or uuid4())
    conversation_id = str(data.conversation_id) if data.conversation_id else None
    query = select(ChatExchange).where(*thread_filters(user.id, data.tree_id, conversation_id))
    def check_conversation():
        existing_thread = data.require_existing or (conversation_id and conversation_id != request_id)
        if existing_thread and db.scalar(query.limit(1)) is None:
            raise HTTPException(404, 'Разговорът е изтрит.')
    existing_query=select(ChatExchange).where(ChatExchange.user_id==user.id,ChatExchange.request_id==request_id)
    def existing_response(row):
        if row.tree_id!=data.tree_id or row.conversation_id!=conversation_id or row.question!=data.message:
            raise HTTPException(status_code=409,detail='Тази заявка вече е използвана.')
        return exchange_json(row)
    existing=db.scalar(existing_query)
    if existing is not None:
        return existing_response(existing)
    check_conversation()
    if not data.report and not assistant_provider():
        raise HTTPException(status_code=503,detail='Облачният чат очаква настройка на Cloudflare в Render. Можеш да използваш справките.')
    devices=[]
    for tree in ([focus] if focus is not None else accessible_trees(db,user)):
        device=to_tree(db,tree,user.id)
        device['maintenance']=maintenance_for(db,tree)
        if not data.report:
            alerts=db.scalars(select(Alert).where(Alert.tree_id==tree.id).order_by(desc(Alert.id)).limit(10)).all()
            device['recent_alerts']=[{'message':a.message,'severity':a.severity,'acknowledged':a.acknowledged,
                                      'time':a.created_at.isoformat()+'Z'} for a in alerts]
            oxygen=tree_oxygen(tree.id,240,db,user)
            points=oxygen.pop('points')
            device['oxygen_history']={**oxygen,'from':points[0]['time'] if points else None,
                                       'to':points[-1]['time'] if points else None}
            device['monthly_archive']=[]
            months=archive_months()
            question=data.message.casefold()
            bulgarian_months='януари февруари март април май юни юли август септември октомври ноември декември'.split()
            english_months='january february march april may june july august september october november december'.split()
            for month in months:
                entry=monthly_archive(tree,month)
                index=int(month[-2:])-1
                requested=any(term in question for term in (month,bulgarian_months[index],english_months[index]))
                previous=month==months[1] and any(term in question for term in ('last month','миналия месец','предходния месец'))
                if not (requested or previous):
                    entry.pop('days')
                device['monthly_archive'].append(entry)
            device['forecast']=tree_forecast(tree.id,db,user)
            device['daily_energy_outlook']=energy_outlook(
                db, tree, device['latest']['source'] if device['latest'] else None, datetime.now(timezone.utc))
            rows=recent_readings(db,tree,96,device['latest']['source']) if device['latest'] else []
            if rows:
                device['recent_power']={'from':rows[-1].time.isoformat()+'Z','to':rows[0].time.isoformat()+'Z',
                                        'samples':len(rows),'min_w':min(r.power_w for r in rows),
                                        'max_w':max(r.power_w for r in rows),'mean_w':round(sum(r.power_w for r in rows)/len(rows),1)}
        devices.append(device)
    if data.report:
        result={'reply':account_report(data.report,devices,data.language),'mode':'report'}
    else:
        recent=db.scalars(query.order_by(desc(ChatExchange.id)).limit(4)).all()
        history=[]
        for row in reversed(recent):
            history.extend([{'role':'user','content':row.question},{'role':'assistant','content':row.reply}])
        context={'account':{'name':user.name,'role':user.role},'focus_tree_id':data.tree_id,'trees':devices,'reply_language':data.language}
        try:
            result=answer(data.message,context,history)
        except AssistantAPIError as exc:
            # Categorized provider failure; never reveal API keys or raw response bodies.
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except Exception:
            logging.getLogger(__name__).exception('Unexpected failure in /api/chat')
            raise HTTPException(status_code=502, detail='Неочаквана сървърна грешка при AI разговора. Виж терминала на FastAPI за подробности.')
    lock_chat_owner(db, user.id)
    check_conversation()
    exchange=ChatExchange(conversation_id=conversation_id,user_id=user.id,tree_id=data.tree_id,request_id=request_id,question=data.message,
                          reply=result['reply'],mode=result['mode'],model=result.get('model'))
    db.add(exchange)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing=db.scalar(existing_query)
        if existing is None:
            raise
        return existing_response(existing)
    return exchange_json(exchange)




class Upload(BaseModel):
    name: str = Field(min_length=1,max_length=180)
    content: str = Field(min_length=1,max_length=6990508)


def save_support_message(db,t,by_agent,data):
    uploads=([data.file] if data.file else [])+data.files
    if not uploads:
        db.add(SupportMessage(ticket=t.id,by_agent=by_agent,body=data.body))
        return
    remaining=5*1024*1024
    for index,upload in enumerate(uploads):
        try:
            content=base64.b64decode(upload.content,validate=True)
        except ValueError:
            raise HTTPException(422,'Невалиден файл.')
        remaining-=len(content)
        if remaining<0:
            raise HTTPException(413,'Файловете трябва да са до 5 MB общо.')
        message=SupportMessage(ticket=t.id,by_agent=by_agent,body=data.body if index==0 else upload.name)
        db.add(message)
        db.flush()
        db.add(SupportFile(message=message.id,name=upload.name,content=content))



class TicketInput(BaseModel):
    files: list[Upload] = Field(default_factory=list)
    file: Upload | None = None
    category: Literal['account','connection','performance','warranty','other']
    channel: Literal['ticket','chat']
    subject: Annotated[str, StringConstraints(strip_whitespace=True,min_length=2,max_length=140)]
    body: Annotated[str, StringConstraints(strip_whitespace=True,min_length=1,max_length=4000)]
    tree_id: int | None = None


class SupportReply(BaseModel):
    files: list[Upload] = Field(default_factory=list)
    file: Upload | None = None
    body: Annotated[str, StringConstraints(strip_whitespace=True,min_length=1,max_length=4000)]


class PhotoInput(BaseModel):
    image: Annotated[str, StringConstraints(max_length=90000)]


def profile_photo(db,owner):
    photo=db.get(AccountPhoto,owner) if owner else None
    return photo.image if photo else None


@app.get('/api/profile/photo')
def my_photo(db:Session=Depends(get_db),user:User=Depends(logged_in)):
    return {'image':profile_photo(db,user.id)}


@app.put('/api/profile/photo')
def save_photo(data:PhotoInput,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    try:
        raw=base64.b64decode(data.image,validate=True)
        with Image.open(io.BytesIO(raw),formats=['JPEG','PNG','WEBP']) as image:
            if max(image.size)>1024: raise ValueError()
            square=ImageOps.fit(image.convert('RGB'),(96,96))
            output=io.BytesIO()
            square.save(output,format='JPEG',quality=85)
    except (ValueError,OSError,Image.DecompressionBombError):
        raise HTTPException(422,'Невалидно изображение.')
    avatar='data:image/jpeg;base64,'+base64.b64encode(output.getvalue()).decode()
    db.merge(AccountPhoto(owner=user.id,image=avatar))
    db.commit()
    return {'image':avatar}


def support_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@app.middleware('http')
async def private_support_responses(request:Request,call_next):
    response=await call_next(request)
    if request.url.path.startswith('/api/support'):
        response.headers['Cache-Control']='private, no-store'
    return response


def expire_chats(db):
    cutoff=support_now()-timedelta(minutes=5)
    expired=select(LiveLease.ticket).where(LiveLease.agent_seen<=cutoff,LiveLease.agent_seen>=LiveLease.customer_seen)
    db.execute(update(SupportTicket).where(SupportTicket.closed.is_(False),SupportTicket.id.in_(expired)).values(closed=True))
    db.commit()


@app.post('/api/support/presence')
def support_presence(db:Session=Depends(get_db),user:User=Depends(logged_in)):
    if not db.get(SupportAgent,user.id):
        raise HTTPException(403,'Само за агенти.')
    db.merge(SupportPresence(agent=user.id,seen=support_now()))
    db.commit()
    return {'ok':True}


def ticket_json(db,t,viewer):
    visible=t.channel!="chat" or t.owner==viewer or (t.agent==viewer and not t.closed)
    warranty=db.get(DeviceWarranty,t.serial) if visible and t.serial else None
    return dict(id=t.id,subject=t.subject,category=t.category,channel=t.channel,model=t.model if visible else None,serial=t.serial if visible else None,
                warranty=warranty.valid_until.date().isoformat() if warranty else None,
                customer=db.get(User,t.owner).name,agent=db.get(User,t.agent).name if t.agent else None,closed=t.closed)


def support_ticket(db,user,ticket_id,lock=False):
    expire_chats(db)
    query=select(SupportTicket).where(SupportTicket.id==ticket_id)
    ticket=db.scalar(query.with_for_update() if lock else query)
    if not ticket or (ticket.owner!=user.id and not db.get(SupportAgent,user.id)):
        raise HTTPException(404,'Запитването не е намерено.')
    if ticket.channel=="chat" and (ticket.closed or (ticket.owner!=user.id and ticket.agent not in (None,user.id))):
        raise HTTPException(404,"Сесията не е достъпна.")
    return ticket


@app.get('/api/support')
def support_list(db:Session=Depends(get_db),user:User=Depends(logged_in)):
    agent=bool(db.get(SupportAgent,user.id))
    expire_chats(db)
    query=select(SupportTicket)
    query=query.where(or_(SupportTicket.channel!="chat",SupportTicket.closed.is_(False)))
    if not agent: query=query.where(SupportTicket.owner==user.id)
    else: query=query.where(or_(SupportTicket.owner==user.id,SupportTicket.channel!='chat',
                               (SupportTicket.closed.is_(False) & or_(SupportTicket.agent.is_(None),SupportTicket.agent==user.id))))
    online=db.scalar(select(func.count()).select_from(SupportPresence).where(SupportPresence.seen>support_now()-timedelta(seconds=45)))
    return {'agent':agent,'online':bool(online),'tickets':[ticket_json(db,t,user.id) for t in db.scalars(query.order_by(SupportTicket.id.desc()))]}


@app.post('/api/support')
def new_ticket(data:TicketInput,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    tree=find_tree(db,data.tree_id,user) if data.tree_id is not None else None
    t=SupportTicket(owner=user.id,category=data.category,channel=data.channel,subject=data.subject,
                    serial=tree.code if tree else None,model=get_model(tree.model_code,tree.code)['name'] if tree else None)
    db.add(t);db.flush()
    if t.channel=="chat":
        db.add(LiveLease(ticket=t.id,tree_id=data.tree_id,customer_seen=support_now()))
    save_support_message(db,t,False,data)
    db.commit()
    return {'id':t.id}


@app.get('/api/support/archive')
def support_archive(db:Session=Depends(get_db),user:User=Depends(logged_in)):
    if not db.get(SupportAgent,user.id): raise HTTPException(403,'Само за поддръжката.')
    expire_chats(db)
    rows=db.execute(select(SupportTicket.id,SupportTicket.category,ChatConnection.accepted)
        .outerjoin(ChatConnection,ChatConnection.ticket==SupportTicket.id)
        .where(SupportTicket.channel=='chat',SupportTicket.closed.is_(True))
        .order_by(SupportTicket.id.desc()))
    return [dict(id=r.id,category=r.category,accepted=r.accepted.isoformat()+'Z' if r.accepted else None) for r in rows]


@app.get('/api/support/notices')
def support_notices(db:Session=Depends(get_db),user:User=Depends(logged_in)):
    rows=db.scalars(select(ChatConnection).join(SupportTicket,SupportTicket.id==ChatConnection.ticket)
        .where(SupportTicket.owner==user.id,ChatConnection.dismissed.is_(False)).order_by(ChatConnection.accepted.desc()))
    return [dict(id=r.ticket,time=r.accepted.isoformat()+'Z') for r in rows]


@app.post('/api/support/{ticket_id}/dismiss')
def dismiss_notice(ticket_id:int,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    row=db.get(SupportTicket,ticket_id)
    notice=db.get(ChatConnection,ticket_id)
    if not row or row.owner!=user.id or not notice: raise HTTPException(404)
    notice.dismissed=True
    db.commit()
    return {'ok':True}


@app.delete('/api/support/{ticket_id}')
def delete_inquiry(ticket_id:int,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    row=support_ticket(db,user,ticket_id,True)
    if row.channel!='ticket' or row.owner!=user.id: raise HTTPException(403)
    db.execute(delete(SupportFile).where(SupportFile.message.in_(select(SupportMessage.id).where(SupportMessage.ticket==ticket_id))))
    db.execute(delete(SupportMessage).where(SupportMessage.ticket==ticket_id))
    db.delete(row)
    db.commit()
    return {'ok':True}


@app.post('/api/support/{ticket_id}/accept')
def accept_chat(ticket_id:int,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    t=support_ticket(db,user,ticket_id,True)
    if t.owner==user.id or t.channel!='chat' or t.closed:
        raise HTTPException(403,'Сесията не може да бъде приета.')
    claimed=db.execute(update(SupportTicket).where(SupportTicket.id==t.id,SupportTicket.agent.is_(None),
                       SupportTicket.closed.is_(False)).values(agent=user.id))
    if not claimed.rowcount: raise HTTPException(409,'Сесията вече е поета.')
    lease=db.get(LiveLease,t.id)
    if not lease:  # A request opened before live windows were introduced.
        lease=LiveLease(ticket=t.id,customer_seen=support_now())
        db.add(lease)
    lease.agent_seen=support_now()
    db.add(ChatConnection(ticket=t.id))
    db.commit()
    return {'ok':True}


@app.post('/api/support/{ticket_id}/typing')
def chat_typing(ticket_id:int,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    t=support_ticket(db,user,ticket_id,True)
    lease=db.get(LiveLease,t.id)
    if t.channel!='chat' or not t.agent or user.id not in (t.owner,t.agent) or not lease:
        raise HTTPException(409,'Сесията не е активна.')
    connection=db.get(ChatConnection,t.id)
    if not connection:
        connection=ChatConnection(ticket=t.id,dismissed=True)
        db.add(connection)
    now=support_now()
    if user.id==t.owner: connection.customer_typing=now
    else: connection.agent_typing=now
    db.commit()
    return {'ok':True}


def agent_score(db,agent):
    mean,count=db.execute(select(func.avg(ChatRating.stars),func.count(ChatRating.ticket))
        .join(SupportTicket,SupportTicket.id==ChatRating.ticket).where(SupportTicket.agent==agent)).one()
    return {'average':round(float(mean),1) if count else None,'count':count}


@app.get('/api/profile/support-rating')
def profile_support_rating(db:Session=Depends(get_db),user:User=Depends(logged_in)):
    return agent_score(db,user.id) if db.get(SupportAgent,user.id) else None


class RatingInput(BaseModel):
    stars: int = Field(ge=1,le=5,strict=True)


def rateable_ticket(db,user,ticket_id):
    ticket=db.scalar(select(SupportTicket).where(SupportTicket.id==ticket_id).with_for_update())
    if not ticket or ticket.owner!=user.id or ticket.channel!='chat' or not ticket.closed or not ticket.agent:
        raise HTTPException(404)


@app.get('/api/support/{ticket_id}/rating')
def read_chat_rating(ticket_id:int,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    rateable_ticket(db,user,ticket_id)
    rating=db.get(ChatRating,ticket_id)
    return {'stars':rating.stars if rating else None}


@app.put('/api/support/{ticket_id}/rating')
def rate_chat(ticket_id:int,data:RatingInput,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    rateable_ticket(db,user,ticket_id)
    db.merge(ChatRating(ticket=ticket_id,stars=data.stars))
    db.commit()
    return {'stars':data.stars}


@app.get('/api/support/{ticket_id}')
def support_thread(ticket_id:int,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    t=support_ticket(db,user,ticket_id)
    messages=db.scalars(select(SupportMessage).where(SupportMessage.ticket==t.id).order_by(SupportMessage.id))
    stats=None
    if t.channel=='chat' and not t.closed and user.id==t.agent:
        lease=db.get(LiveLease,t.id)
        tree=db.get(Tree,lease.tree_id) if lease and lease.tree_id else None
        if tree and tree.code==t.serial and can_read(db,db.get(User,t.owner),tree):
            info=to_tree(db,tree)
            latest=info['latest_sensors'] or info['latest'] or {}
            stats={key:latest.get(key) for key in ('power_w','water_pct','oxygen_flow_lph','time')}
            stats['battery_pct']=(info['simulation'] or {}).get('battery_pct')
    connection=db.get(ChatConnection,t.id) if t.channel=='chat' else None
    typing=(connection.agent_typing if user.id==t.owner else connection.customer_typing) if connection else None
    lease=db.get(LiveLease,t.id) if connection else None
    remaining=None
    if lease and lease.agent_seen and lease.agent_seen>=lease.customer_seen:
        remaining=max(0,300-int((support_now()-lease.agent_seen).total_seconds()))
    files=dict(db.execute(select(SupportFile.message,SupportFile.name).join(SupportMessage,SupportMessage.id==SupportFile.message).where(SupportMessage.ticket==t.id)).all())
    return {**ticket_json(db,t,user.id),'remaining':remaining,'rating':agent_score(db,t.agent) if t.agent else None,'typing':bool(typing and typing>support_now()-timedelta(seconds=5)),
            'customer_photo':profile_photo(db,t.owner),'agent_photo':profile_photo(db,t.agent),'viewer_agent':user.id!=t.owner,'stats':stats,'messages':[dict(id=m.id,agent=m.by_agent,body=m.body,file=files.get(m.id),time=m.created_at.isoformat()+'Z') for m in messages]}


@app.get('/api/support/{ticket_id}/files/{message_id}')
def download_support_file(ticket_id:int,message_id:int,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    t=support_ticket(db,user,ticket_id)
    if t.channel=='chat' and user.id not in (t.agent,t.owner):
        raise HTTPException(404)
    file=db.scalar(select(SupportFile).join(SupportMessage,SupportMessage.id==SupportFile.message)
                   .where(SupportFile.message==message_id,SupportMessage.ticket==t.id))
    if not file: raise HTTPException(404)
    return Response(file.content,media_type='application/octet-stream',headers={'Content-Disposition':'attachment','X-Content-Type-Options':'nosniff'})


@app.post('/api/support/{ticket_id}/reply')
def support_reply(ticket_id:int,data:SupportReply,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    t=support_ticket(db,user,ticket_id,True)
    if t.closed: raise HTTPException(409,'Разговорът е приключен.')
    by_agent=t.owner!=user.id
    if t.channel=="chat" and not t.agent: raise HTTPException(409,"Изчакай агент да приеме сесията.")
    if by_agent:
        if t.agent not in (None,user.id): raise HTTPException(409,'Друг агент работи по случая.')
        t.agent=user.id
    cooling=False
    if t.channel=='chat':
        lease=db.get(LiveLease,t.id)
        connection=db.get(ChatConnection,t.id)
        if lease:
            cooling=bool(not by_agent and connection and lease.customer_seen>connection.accepted and
                         support_now()-lease.customer_seen<timedelta(seconds=2))
            if not by_agent:
                lease.customer_seen=support_now()
                lease.agent_seen=None
            elif lease.agent_seen is None or lease.agent_seen<lease.customer_seen:
                lease.agent_seen=support_now()
        if connection:
            if by_agent: connection.agent_typing=None
            else: connection.customer_typing=None
    save_support_message(db,t,by_agent,data)
    if cooling:
        raise HTTPException(429,'Изчакай 2 секунди между съобщенията.',headers={'Retry-After':'2'})
    db.commit()
    return {'ok':True}


@app.post('/api/support/{ticket_id}/close')
def close_support(ticket_id:int,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    t=support_ticket(db,user,ticket_id,True)
    if user.id not in (t.owner,t.agent): raise HTTPException(403,'Нямаш достъп за приключване.')
    t.closed=True
    db.commit()
    return {'ok':True}

# Serve the built React application from the same HTTPS host as FastAPI. This avoids
# cross-origin cookies and makes mobile QR scanning possible on a single Render URL.
# In local development Vite continues to run independently at 127.0.0.1:5173.
FRONTEND_DIST = Path(__file__).resolve().parents[2] / 'frontend_dist'
if (FRONTEND_DIST / 'index.html').is_file():
    if (FRONTEND_DIST / 'assets').is_dir():
        app.mount('/assets', StaticFiles(directory=str(FRONTEND_DIST / 'assets')), name='frontend-assets')

    @app.get('/', include_in_schema=False)
    def production_home():
        return FileResponse(FRONTEND_DIST / 'index.html', headers={'Cache-Control':'no-cache'})

    @app.get('/Solix.mobileconfig', include_in_schema=False)
    def iphone_home_screen_profile():
        return FileResponse(FRONTEND_DIST / 'Solix.mobileconfig', media_type='application/x-apple-aspen-config',
                            filename='Solix.mobileconfig')

    @app.get('/{spa_path:path}', include_in_schema=False)
    def production_spa(spa_path: str):
        # Keep missing API routes as real 404 responses instead of returning HTML.
        if spa_path.startswith(('api/', 'scan/', 'assets/')):
            raise HTTPException(status_code=404, detail='Not Found')
        resolved = (FRONTEND_DIST / spa_path).resolve()
        if resolved.is_relative_to(FRONTEND_DIST.resolve()) and resolved.is_file():
            return FileResponse(resolved)
        return FileResponse(FRONTEND_DIST / 'index.html', headers={'Cache-Control':'no-cache'})




