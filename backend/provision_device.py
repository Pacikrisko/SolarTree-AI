"""Trusted operator utility; registers hardware before customer QR pairing.
Run from backend directory after installing requirements. Never expose this as a public API.
"""
import argparse
import secrets
from hashlib import sha256
from sqlalchemy import select
from app.database import Base, engine, SessionLocal
from app.models import DeviceRegistration
from app.catalog import MODELS
from app.migrations import upgrade


def main():
    cli=argparse.ArgumentParser(description='Provision Solix device with QR pairing and independent telemetry token')
    cli.add_argument('--code',required=True,help='Unique serial ID e.g. ST-M6-2051')
    cli.add_argument('--model',required=True,choices=MODELS.keys())
    cli.add_argument('--kind',required=True,choices=['private','municipal'])
    cli.add_argument('--qr',default='',help='Optional QR PNG file output (requires pip install qrcode[pil])')
    args=cli.parse_args()
    code=args.code.strip().upper()
    if not (3<=len(code)<=40) or not code.replace('-','').isalnum():
        cli.error('Code must be 3-40 alphanumeric/hyphen characters')
    claim=secrets.token_urlsafe(32)
    telemetry=secrets.token_urlsafe(40)
    Base.metadata.create_all(bind=engine);upgrade(engine)
    with SessionLocal() as db:
        if db.scalar(select(DeviceRegistration).where(DeviceRegistration.code==code)):
            cli.error('This code is already provisioned')
        db.add(DeviceRegistration(code=code,model_code=args.model,kind=args.kind,
            claim_hash=sha256(claim.encode()).hexdigest(),telemetry_hash=sha256(telemetry.encode()).hexdigest()))
        db.commit()
    value=f'STREE1|{code}|{claim}'
    print('Device:',code)
    print('Model:',args.model)
    print('Pairing QR contents:',value)
    print('Device telemetry key (keep PRIVATE, NOT inside the QR):',telemetry)
    if args.qr:
        try:
            import qrcode
        except ImportError:
            cli.error('Install optional QR generator: pip install "qrcode[pil]"')
        qrcode.make(value).save(args.qr)
        print('QR label saved:',args.qr)
    print('IMPORTANT: Securely store the device telemetry key. It cannot be recovered from the database.')

if __name__=='__main__':
    main()
