from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Float, Boolean, UniqueConstraint, Index, Text
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(30), default='owner')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

class GoogleIdentity(Base):
    __tablename__ = 'google_identities'
    subject: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), unique=True, nullable=False)


class Tree(Base):
    __tablename__ = 'trees'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(20))
    owner_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    location: Mapped[str] = mapped_column(String(150))
    model_code: Mapped[str] = mapped_column(String(40), default='ST-M6', server_default='ST-M6')
    media_file: Mapped[str | None] = mapped_column(String(100), nullable=True)
    media_mime: Mapped[str | None] = mapped_column(String(40), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

class Reading(Base):
    __tablename__ = 'readings'
    id: Mapped[int] = mapped_column(primary_key=True)
    tree_id: Mapped[int] = mapped_column(ForeignKey('trees.id'), index=True)
    time: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    power_w: Mapped[float] = mapped_column(Float)
    temperature_c: Mapped[float] = mapped_column(Float)
    humidity_pct: Mapped[float] = mapped_column(Float)
    h2_sensor_value: Mapped[float] = mapped_column(Float)
    water_pct: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(20), default='simulation')
    electrolyzer_power_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    oxygen_flow_lph: Mapped[float | None] = mapped_column(Float, nullable=True)
    oxygen_basis: Mapped[str] = mapped_column(String(16), default='unavailable', server_default='unavailable')

class Alert(Base):
    __tablename__ = 'alerts'
    id: Mapped[int] = mapped_column(primary_key=True)
    tree_id: Mapped[int] = mapped_column(ForeignKey('trees.id'), index=True)
    message: Mapped[str] = mapped_column(String(280))
    severity: Mapped[str] = mapped_column(String(15), default='warning')
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

class Maintenance(Base):
    __tablename__ = 'maintenance'
    __table_args__ = (UniqueConstraint('tree_id', 'component'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tree_id: Mapped[int] = mapped_column(ForeignKey('trees.id'), index=True)
    component: Mapped[str] = mapped_column(String(30))  # water_filter | oxygen_dryer
    last_serviced_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    interval_days: Mapped[int] = mapped_column(default=90)  # schedule estimate, NOT a device sensor

class DeviceRegistration(Base):
    """Pre-provisioned hardware. Claim tokens grant one-time ownership; telemetry keys are separate."""
    __tablename__ = 'device_registrations'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    model_code: Mapped[str] = mapped_column(String(40))
    kind: Mapped[str] = mapped_column(String(20))
    claim_hash: Mapped[str] = mapped_column(String(64))
    telemetry_hash: Mapped[str] = mapped_column(String(64))
    bound_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    claimed_tree_id: Mapped[int | None] = mapped_column(ForeignKey('trees.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class MobilePairSession(Base):
    """Short-lived, single-use desktop-to-phone pairing. Never stores claim codes."""
    __tablename__ = 'mobile_pair_sessions'
    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(16), default='pending')
    tree_id: Mapped[int | None] = mapped_column(ForeignKey('trees.id'), nullable=True)
    attempts: Mapped[int] = mapped_column(default=0)

class DeviceSample(Base):
    """Authentic Pico sensor values; absent sensors are NULL, not fabricated readings."""
    __tablename__ = 'device_samples'
    id: Mapped[int] = mapped_column(primary_key=True)
    tree_id: Mapped[int] = mapped_column(ForeignKey('trees.id'), index=True)
    time: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    mq8_adc_raw: Mapped[int | None] = mapped_column(nullable=True)
    power_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    water_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    oxygen_flow_lph: Mapped[float | None] = mapped_column(Float, nullable=True)


class ChatExchange(Base):
    __tablename__ = 'chat_exchanges'
    __table_args__ = (
        UniqueConstraint('user_id', 'request_id'),
        Index('ix_chat_owner_scope_id', 'user_id', 'tree_id', 'id'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    tree_id: Mapped[int | None] = mapped_column(ForeignKey('trees.id'), nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    request_id: Mapped[str] = mapped_column(String(36))
    question: Mapped[str] = mapped_column(Text)
    reply: Mapped[str] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(String(12))
    model: Mapped[str | None] = mapped_column(String(150), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
