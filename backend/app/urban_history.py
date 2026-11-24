"""Synthetic readings for the Urban demonstration and optional local demo fixtures."""
import math
import random
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from .models import Tree, Reading
from .catalog import get_model
from .resource_math import (
    O2_MOLAR_VOLUME_L, WATER_MOLAR_MASS_G, NORMAL_PRESSURE_BAR,
    NORMAL_TEMP_K, TANK_TEMP_K, H2_LHV_KWH_PER_NORMAL_M3,
)


URBAN_DAYLIGHT_HOURS = 12


def is_urban_simulator(tree: Tree) -> bool:
    return tree.code == 'URBAN-TREE-0001' and tree.model_code == 'ST-URBAN-2KW'


def urban_sample(tree: Tree, when: datetime):
    """A repeatable 24-hour operating cycle. All timestamps are naive UTC, as in Reading."""
    model = get_model(tree.model_code)
    # Scenario sunrise is 05:00 UTC. Start with a full water tank at each sunrise.
    hour = (when.hour + when.minute / 60 - 5) % 24
    phase = math.pi * min(hour, URBAN_DAYLIGHT_HOURS) / URBAN_DAYLIGHT_HOURS
    sunlight = max(0.0, math.sin(phase)) if hour < URBAN_DAYLIGHT_HOURS else 0.0
    rated_electrolyzer_w = model['electrolyzer_kw'] * 1000
    solar_w = model['rated_solar_w'] * sunlight
    electrolyzer_w = rated_electrolyzer_w * sunlight
    oxygen_lph = model['oxygen_nominal_lph'] * sunlight
    # Integrate the same daylight curve used for the instantaneous gas flows.
    oxygen_since_dawn = model['oxygen_nominal_lph'] * URBAN_DAYLIGHT_HOURS / math.pi * (1 - math.cos(phase))
    water_used_l = oxygen_since_dawn * 2 * WATER_MOLAR_MASS_G / O2_MOLAR_VOLUME_L / 1000
    water_pct = 100 * (1 - water_used_l / model['water_tank_l'])
    # Constant demonstration fuel-cell load consumes one day's simulated H2 output per day.
    fuel_use_nlph = 2 * model['oxygen_nominal_lph'] / math.pi
    stored_h2_nl = 240 + 2 * oxygen_since_dawn - fuel_use_nlph * hour
    normal_l_per_bar = model['hydrogen_tank_l'] * NORMAL_TEMP_K / (NORMAL_PRESSURE_BAR * TANK_TEMP_K)
    signal = 0.09 + 0.012 * sunlight + 0.004 * math.sin(2 * math.pi * hour / 3)
    lagged_heat = math.sin(2 * math.pi * (hour - 4) / 24)
    sample = Reading(
        id=-int((when - datetime(1970, 1, 1)).total_seconds() // 60),
        tree_id=tree.id, time=when, source='simulation', oxygen_basis='simulation',
        power_w=round(solar_w, 1), electrolyzer_power_w=round(electrolyzer_w, 1),
        oxygen_flow_lph=round(oxygen_lph, 2), water_pct=round(water_pct, 1),
        temperature_c=round(20 + 5 * lagged_heat, 1), humidity_pct=round(55 - 11 * lagged_heat, 1),
        h2_sensor_value=round(signal, 4),
    )
    operating = {
        'hydrogen_pressure_bar_g': round(stored_h2_nl / normal_l_per_bar, 1),
        'fuel_cell_load_kw': round(fuel_use_nlph * H2_LHV_KWH_PER_NORMAL_M3 * 0.5 / 1000, 3),
        'hydrogen_flow_nlph': round(2 * oxygen_lph, 1),
        'mq8_adc_raw': round(signal * 65535),
    }
    return sample, operating


def urban_readings(tree: Tree, limit: int, now: datetime | None = None):
    """Most recent first: current minute, then completed quarter-hour samples."""
    end = (now or datetime.now(timezone.utc)).replace(tzinfo=None, second=0, microsecond=0)
    previous = end - timedelta(minutes=end.minute % 15 or 15)
    stamps = [end] + [previous - timedelta(minutes=15 * i) for i in range(min(limit, 96) - 1)]
    return [urban_sample(tree, stamp)[0] for stamp in stamps]


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
