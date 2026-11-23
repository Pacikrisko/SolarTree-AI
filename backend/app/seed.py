import math
import random
import os
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .models import User, Tree, Reading, DeviceRegistration
from hashlib import sha256
from .security import hash_password

DEMO_MODE = os.getenv('DEMO_MODE', 'true').lower() == 'true'


def seed_demo(db: Session):
    if not DEMO_MODE:
        return
    for code, model, kind, claim, device in [
        ('ST-M6-1001','ST-M6','private','DEMO-PRIVATE-PAIR-2026','DEMO-PRIVATE-DEVICE-KEY-2026'),
        ('ST-M8-2001','ST-M8','municipal','DEMO-MUNICIPAL-PAIR-2026','DEMO-MUNICIPAL-DEVICE-KEY-2026'),
        ('IVAN-TREE-0001','ST-IVAN-P1','private','IVAN-PROTOTYPE-PAIR-2026','IVAN-PROTOTYPE-DEVICE-KEY-2026'),
        ('URBAN-TREE-0001','ST-URBAN-2KW','private','URBAN-2KW-PAIR-2026','URBAN-2KW-DEVICE-KEY-2026'),
    ]:
        if not db.scalar(select(DeviceRegistration).where(DeviceRegistration.code==code)):
            db.add(DeviceRegistration(code=code,model_code=model,kind=kind,claim_hash=sha256(claim.encode()).hexdigest(),telemetry_hash=sha256(device.encode()).hexdigest()))
    db.commit()
    if db.scalar(select(func.count()).select_from(User)):
        return
    staff = User(name='Оператор на мрежата', email='municipality@demo.bg', password_hash=hash_password('Demo12345!'), role='municipality')
    owner = User(name='Частен собственик', email='owner@demo.bg', password_hash=hash_password('Demo12345!'), role='owner')
    db.add_all([staff, owner]); db.flush()
    trees = [
        Tree(code='STZ-001', name='Централен площад', kind='municipal', owner_id=None, model_code='ST-M8', location='Централна градска зона, Стара Загора', lat=42.4245, lng=25.6232),
        Tree(code='STZ-002', name='Парк Аязмото', kind='municipal', owner_id=None, model_code='ST-M8', location='Район Аязмото, Стара Загора', lat=42.4433, lng=25.6313),
        Tree(code='STZ-003', name='Квартал Железник', kind='municipal', owner_id=None, model_code='ST-M8', location='Железник, Стара Загора', lat=42.4300, lng=25.5760),
        Tree(code='HOME-001', name='Моето соларно дърво', kind='private', owner_id=owner.id, model_code='ST-M6', location='Частен обект', lat=None, lng=None),
    ]
    db.add_all(trees); db.flush()
    rng = random.Random(2026)
    end = datetime.now(timezone.utc).replace(tzinfo=None, minute=0, second=0, microsecond=0)
    readings = []
    for t in trees:
        for i in range(120):
            ts = end - timedelta(minutes=15 * (119-i))
            clock = ts.hour + ts.minute/60
            sun = max(0, math.sin(math.pi*(clock-6)/13)) if 6 <= clock <= 19 else 0
            maxpower = 1500 if t.kind == 'municipal' else 650
            power = max(0, (maxpower * sun * (0.83 + rng.random()*.17)) + rng.gauss(0,20)) if sun > 0 else 0
            readings.append(Reading(tree_id=t.id, time=ts, power_w=round(power, 1),
                temperature_c=round(17 + 9*sun + rng.random()*2, 1), humidity_pct=round(53-18*sun+rng.random()*5, 1),
                h2_sensor_value=round(0.08+rng.random()*.04, 3), water_pct=round(87-i*.06+rng.random()*.6, 1), source='simulation', electrolyzer_power_w=round(power*.65,1),
                oxygen_flow_lph=round(power*.065,1), oxygen_basis='simulation'))
    db.add_all(readings);db.commit()
