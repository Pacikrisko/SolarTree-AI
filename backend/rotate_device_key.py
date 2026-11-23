"""Service utility to rotate a device's API key without unpairing it.
Run locally: python rotate_device_key.py --code IVAN-TREE-0001
Never store the printed key in QR labels or publish it.
"""
import argparse
import secrets
from hashlib import sha256
from sqlalchemy import select
from app.database import Base,engine,SessionLocal
from app.models import DeviceRegistration
from app.migrations import upgrade

cli=argparse.ArgumentParser()
cli.add_argument('--code',required=True)
args=cli.parse_args()
Base.metadata.create_all(bind=engine);upgrade(engine)
with SessionLocal() as db:
    dev=db.scalar(select(DeviceRegistration).where(DeviceRegistration.code==args.code.strip().upper()))
    if not dev: cli.error('Device is not registered')
    key=secrets.token_urlsafe(40)
    dev.telemetry_hash=sha256(key.encode()).hexdigest()
    db.commit()
    print('Device:',dev.code)
    print('New telemetry key (copy NOW; not stored in plaintext):',key)
    print('Any previous device key is now invalid.')
