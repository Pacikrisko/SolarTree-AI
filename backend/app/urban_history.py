"""Optional educational history, explicitly synthetic; only active in DEMO_MODE."""
import math
import random
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from .models import Tree, Reading
from .resource_math import O2_MOLAR_VOLUME_L, WATER_MOLAR_MASS_G


def add_demo_urban_history(db:Session, tree:Tree) -> None:
    if tree.model_code!='ST-URBAN-2KW':
        return
    rng=random.Random(tree.id*97+2026)
    end=datetime.now(timezone.utc).replace(tzinfo=None,second=0,microsecond=0)
    # 24h history, quarter-hour spacing. 10 L tank begins full and only decreases while producing.
    water_l=10.0
    for i in range(96):
        t=end-timedelta(minutes=15*(95-i))
        hour=t.hour+t.minute/60
        sun=max(0.0,math.sin(math.pi*(hour-7)/11)) if 7<=hour<=18 else 0
        power=max(0.0,min(3200,3200*sun*(.90+.10*rng.random())))
        electrolyzer=min(2000,power*.78)
        oxygen=min(250,250*electrolyzer/2000) if electrolyzer>300 else 0.0
        consumption=oxygen/O2_MOLAR_VOLUME_L*2*WATER_MOLAR_MASS_G/1000*.25
        water_l=max(0.0,water_l-consumption)
        db.add(Reading(tree_id=tree.id,time=t,power_w=round(power,1),temperature_c=round(18+10*sun+rng.random(),1),
                       humidity_pct=round(48-12*sun+rng.random()*4,1),h2_sensor_value=round(.08+.02*rng.random(),3),
                       water_pct=round(water_l*10,1),oxygen_flow_lph=round(oxygen,1),
                       electrolyzer_power_w=round(electrolyzer,1),source='simulation',oxygen_basis='simulation'))
