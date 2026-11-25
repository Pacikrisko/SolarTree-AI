"""SolarTree AI API: account-scoped monitoring; advisory-only analytics and chat."""
import os
from pathlib import Path
from uuid import UUID, uuid4
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
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func, update, or_, delete
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from .database import Base, engine, get_db, SessionLocal
from .models import TreeMember, PairInvite, User, Tree, Reading, Alert, Maintenance, DeviceRegistration, MobilePairSession, DeviceSample, ChatExchange
from .seed import DEMO_MODE, seed_demo
from .google_login import google_client_id, google_user, verified_claims
from .password_reset import router as password_reset_router
from .security import hash_password, verify_password, create_token, current_user, require_user
from .ml import predict_power, detect_anomaly
from .maintenance import initialize_maintenance, maintenance_for, COMPONENTS
from .energy_outlook import energy_outlook
from .assistant import answer, account_report, assistant_provider, AssistantAPIError
from .catalog import get_model, MODELS
from .resource_math import resource_estimate
from .urban_history import add_demo_urban_history, is_urban_simulator, urban_readings, urban_sample
from .migrations import upgrade
from .model_media import find_model_media, media_kind
from .mobile_scanner import scanner_page

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    upgrade(engine)
    with SessionLocal() as db:
        seed_demo(db)
        initialize_maintenance(db)
    yield

app = FastAPI(title='SolarTree AI', version='0.8.0-deploy', lifespan=lifespan)
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
    return can_read(db,user,tree)  # Only advisory UI and service records, NEVER direct plant safety control

def accessible_trees(db: Session, user: User):
    kind = 'municipal' if user.role=='municipality' else 'private'
    return db.scalars(select(Tree).where(or_(Tree.owner_id==user.id,Tree.id.in_(select(TreeMember.tree_id).where(TreeMember.user_id==user.id))),Tree.kind==kind).order_by(Tree.id)).all()
def find_tree(db: Session, tree_id: int, user: User) -> Tree:
    tree = db.get(Tree,tree_id)
    # Return 404 rather than revealing existence of an unauthorized tree.
    if not tree or not can_read(db,user,tree):
        raise HTTPException(status_code=404,detail='Дървото не е намерено в твоя профил.')
    return tree

def to_tree(db: Session, tree: Tree):
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
    return {'id':tree.id,'code':tree.code,'name':tree.name,'kind':tree.kind,
            'model':get_model(tree.model_code),
            'location':tree.location,'lat':tree.lat,'lng':tree.lng,
            'latest':to_reading(last) if last else None,
            'simulation':operating, 'open_alerts':open_alerts,
            'media_kind': media_kind(tree.model_code),
            'service_attention':sum(s['status']!='ok' for s in services),
            'latest_sensors':({
              'time':sensor.time.isoformat()+'Z', 'temperature_c':sensor.temperature_c,
              'humidity_pct':sensor.humidity_pct,'mq8_adc_raw':sensor.mq8_adc_raw,
              'power_w':sensor.power_w,'water_pct':sensor.water_pct,
              'oxygen_flow_lph':sensor.oxygen_flow_lph} if sensor else None),
            'connection':'live' if device_fresh else 'model' if last and last.source=='simulation' else 'offline'}

def logged_in(db:Session=Depends(get_db),authorization:str|None=Header(default=None)):
    return require_user(current_user(db,authorization))

def verify_pair(db: Session, code: str, claim: str, user: User) -> DeviceRegistration:
    reg=db.scalar(select(DeviceRegistration).where(DeviceRegistration.code==code.strip().upper()))
    # Identical errors for unrecognized/incorrect keys; never enumerate inventory from user input.
    digest = sha256(claim.encode()).hexdigest()
    invite = db.get(PairInvite,digest)
    if not reg or not (compare_digest(reg.claim_hash,digest) or (invite and invite.registration_id==reg.id)):
        raise HTTPException(status_code=404,detail='Неуспешно сдвояване. Провери QR кода и кода за регистрация.')
    if reg.claimed_tree_id and reg.model_code in ('ST-IVAN-P1','ST-URBAN-2KW'):
        members = db.scalars(select(TreeMember.user_id).where(TreeMember.tree_id==reg.claimed_tree_id)).all()
        if user.id in members or reg.bound_user_id==user.id:
            raise HTTPException(409,'Дървото вече е добавено в профила.')
        if len(members)>=2:
            raise HTTPException(409,'Дървото вече е добавено в три профила.')
    elif reg.claimed_tree_id is not None or reg.bound_user_id not in (None,user.id):
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
        db.add(TreeMember(tree_id=reg.claimed_tree_id,user_id=user.id))
        db.flush()
        return db.get(Tree,reg.claimed_tree_id)
    # Reserve the inventory row before inserting a tree, even for simultaneous claims.
    reserved=db.execute(update(DeviceRegistration).where(
        DeviceRegistration.id==reg.id, DeviceRegistration.claimed_tree_id.is_(None),
        or_(DeviceRegistration.bound_user_id.is_(None),DeviceRegistration.bound_user_id==user.id)
    ).values(bound_user_id=user.id))
    if reserved.rowcount!=1:
        raise HTTPException(status_code=409,detail='Това устройство вече е регистрирано.')
    if tree.code == 'IVAN-TREE-0001' and tree.lat is None and tree.lng is None:
        tree.lat, tree.lng, tree.location = 42.4258, 25.6345, 'Stara Zagora'
    db.add(tree)
    db.flush()
    reg.claimed_tree_id=tree.id
    return tree

@app.get('/api/health')
def health():
    provider=assistant_provider()
    return {'ok':True,'real_llm':bool(provider),'ai_provider':provider,'simulation_enabled':DEMO_MODE,
            'version':'0.8.0-deploy'}
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
        logging.exception('SolarTree registration integrity error')
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
    return {'code':reg.code,'model':get_model(reg.model_code),'kind':reg.kind}

class ScanIn(BaseModel):
    payload: str = Field(min_length=15,max_length=1000)

class SensorIn(BaseModel):
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
            'tree_name':tree.name if tree else None,'model':get_model(tree.model_code)['name'] if tree else None}

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
              name=get_model(reg.model_code)['name'],location='Добавено чрез QR')
    candidate=tree
    tree=attach_device(db,reg,user,tree,claim)
    session.status='completed';session.tree_id=tree.id
    if DEMO_MODE and candidate is tree and not is_urban_simulator(tree): add_demo_urban_history(db,tree)
    db.commit();initialize_maintenance(db)
    return {'ok':True,'name':tree.name,'model':get_model(tree.model_code)['name']}

@app.get('/api/trees/{tree_id}/resources')
def resources(tree_id: int, water_fill_pct: float = Query(default=100.0, ge=0, le=100),
              pressure_bar_g: float | None = Query(default=None, ge=0, le=500),
              fuel_cell_load_kw: float | None = Query(default=None, ge=0),
              efficiency: float = Query(default=0.50, gt=0, le=1),
              db: Session = Depends(get_db), user: User = Depends(logged_in)):
    tree = find_tree(db, tree_id, user)
    model = get_model(tree.model_code)
    if not model.get('water_tank_l') or not model.get('hydrogen_tank_l'):
        raise HTTPException(status_code=404, detail='За този модел няма данни за резервоарите.')
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
    return [to_tree(db,t) for t in accessible_trees(db,user)]
@app.post('/api/trees',status_code=201)
def create_tree(data:TreeIn,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    # One-time claim must be serialized: only one user can redeem a manufacturing QR.
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
    return to_tree(db,tree)
class CoordinatesIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


@app.patch('/api/trees/{tree_id}/coordinates')
def set_coordinates(tree_id:int, data:CoordinatesIn, db:Session=Depends(get_db), user:User=Depends(logged_in)):
    tree=find_tree(db,tree_id,user)
    if not can_manage(db,user,tree):
        raise HTTPException(403, 'Нямаш достъп за промяна на местоположението.')
    tree.lat,tree.lng=data.lat,data.lng
    db.commit()
    return {'ok':True}


@app.delete('/api/trees/{tree_id}')
def remove_tree(tree_id:int,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    db.scalar(select(DeviceRegistration).where(DeviceRegistration.claimed_tree_id==tree_id).with_for_update())
    tree=db.scalar(select(Tree).where(Tree.id==tree_id).with_for_update())
    if tree is None or not can_manage(db,user,tree):
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

@app.get('/api/trees/{tree_id}')
def tree_detail(tree_id:int,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    return to_tree(db,find_tree(db,tree_id,user))
@app.get('/api/trees/{tree_id}/config')
def get_tree_config(tree_id:int,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    tree=find_tree(db,tree_id,user)
    return {'tree_id':tree.id,**get_model(tree.model_code)}

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
    rows=recent_readings(db,tree,limit)
    return [to_reading(r) for r in reversed(rows)]
@app.get('/api/trees/{tree_id}/oxygen')
def tree_oxygen(tree_id:int,limit:int=240,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    tree=find_tree(db,tree_id,user)
    last=latest_reading(db,tree)
    # Keep virtual history and device telemetry separate; never report a mixed total as measured.
    if last is None:
        return {'tree_id':tree.id,'points':[],'total_l':0,'current_flow_lph':None,
                'basis':'unavailable','note':'Няма налични измервания.'}
    rows=list(reversed(recent_readings(db,tree,max(2,min(limit,500)),last.source)))
    points=[]; total=0.0; prev=None
    for r in rows:
        if r.oxygen_flow_lph is None:
            prev=None
            continue
        if prev is not None:
            delta=(r.time-prev.time).total_seconds()/3600
            if 0<delta<=.5:
                total+=(prev.oxygen_flow_lph+r.oxygen_flow_lph)/2 * delta
        points.append({'time':r.time.isoformat()+'Z','oxygen_flow_lph':round(r.oxygen_flow_lph,2),
                       'cumulative_l':round(total,2),'basis':r.oxygen_basis,'source':r.source})
        prev=r
    return {'tree_id':tree.id,'points':points,'total_l':round(total,2),
            'current_flow_lph':round(points[-1]['oxygen_flow_lph'],2) if points else None,
            'basis':points[-1]['basis'] if points else 'unavailable',
            'note':'Натрупаният обем е изчислен от симулирания дебит за показания период.' if is_urban_simulator(tree) else 'Обемът е изчислен от наличните измервания за показания период; празните интервали не се запълват.'}

@app.get('/api/trees/{tree_id}/forecast')
def tree_forecast(tree_id:int,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    tree=find_tree(db,tree_id,user)
    latest=latest_reading(db,tree)
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
                        'time':a.created_at.isoformat()+'Z','can_ack':True})
    return out
@app.post('/api/alerts/{alert_id}/ack')
def acknowledge(alert_id:int,db:Session=Depends(get_db),user:User=Depends(logged_in)):
    a=db.get(Alert,alert_id)
    if not a:
        raise HTTPException(status_code=404,detail='Няма такова известие.')
    find_tree(db,a.tree_id,user)
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
        raise HTTPException(status_code=409,detail='Този тестов Urban 2K има автоматична симулация.')
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
        raise HTTPException(status_code=409,detail='Този сериен номер е за виртуалния Urban 2K.')
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
        raise HTTPException(status_code=409,detail='Този сериен номер е за виртуалния Urban 2K.')
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
        device=to_tree(db,tree)
        device['maintenance']=maintenance_for(db,tree)
        if not data.report:
            alerts=db.scalars(select(Alert).where(Alert.tree_id==tree.id).order_by(desc(Alert.id)).limit(10)).all()
            device['recent_alerts']=[{'message':a.message,'severity':a.severity,'acknowledged':a.acknowledged,
                                      'time':a.created_at.isoformat()+'Z'} for a in alerts]
            oxygen=tree_oxygen(tree.id,240,db,user)
            points=oxygen.pop('points')
            device['oxygen_history']={**oxygen,'from':points[0]['time'] if points else None,
                                       'to':points[-1]['time'] if points else None}
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

    @app.get('/{spa_path:path}', include_in_schema=False)
    def production_spa(spa_path: str):
        # Keep missing API routes as real 404 responses instead of returning HTML.
        if spa_path.startswith(('api/', 'scan/', 'assets/')):
            raise HTTPException(status_code=404, detail='Not Found')
        resolved = (FRONTEND_DIST / spa_path).resolve()
        if resolved.is_relative_to(FRONTEND_DIST.resolve()) and resolved.is_file():
            return FileResponse(resolved)
        return FileResponse(FRONTEND_DIST / 'index.html', headers={'Cache-Control':'no-cache'})
