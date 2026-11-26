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
    return (tree.code in ('URBAN-TREE-0001', 'URBAN-TREE-0002') or tree.code.startswith('URBAN-SIM-')) and tree.model_code == 'ST-URBAN-2KW'


def urban_sample(tree: Tree, when: datetime):
    """A repeatable 24-hour operating cycle. All timestamps are naive UTC, as in Reading."""
    model = get_model(tree.model_code, tree.code)
    # Daily dispatch model. Quantities below use kWh, normal litres and UTC hours.
    dawn = (when - timedelta(hours=5)).date()
    hour = (when.hour + when.minute / 60 - 5) % 24
    phase = math.pi * min(hour, 12) / 12
    sunlight = math.sin(phase) if hour < 12 else 0.0
    cold = dawn.month in (11, 12, 1, 2)
    solar_peak = model['rated_solar_w'] / 1000 * (.65 if cold else 1)
    solar_w = 1000 * solar_peak * sunlight
    rated = model['electrolyzer_kw']
    yield_l = model['oxygen_nominal_lph'] / rated
    battery_capacity = 8.0
    # Reserve 15% and allocate more stored energy to daytime loads in winter.
    discharge = 5.6 if cold else 2.8
    sun_hours = 24 / math.pi
    day_peak = min(rated, solar_peak + discharge / sun_hours)
    night_kw = rated * .015
    # Extra battery support for the first two hours after sunset.
    dusk_kw = rated * .06
    day_kwh = day_peak * sun_hours
    night_kwh = 2 * dusk_kw + 10 * night_kw
    fuel_kwh_per_litre = H2_LHV_KWH_PER_NORMAL_M3 * .5 / 1000
    daily_h2 = 2 * yield_l * (day_kwh + night_kwh)
    fuel_kw = min(model['fuel_cell_kw'], daily_h2 * fuel_kwh_per_litre / 12)
    # Charging is limited by the nightly energy left after electrolysis.
    swing = min(discharge, max(0, 12 * fuel_kw - night_kwh))
    daylight_fraction = (1 - math.cos(phase)) / 2
    night_hours = max(0, hour - 12)
    night_used = dusk_kw * min(2, night_hours) + night_kw * max(0, night_hours - 2)
    electrolyzer_kw = day_peak * sunlight if hour < 12 else (dusk_kw if hour < 14 else night_kw)
    electrolyzer_w = 1000 * electrolyzer_kw
    oxygen_lph = electrolyzer_kw * yield_l
    oxygen_since_dawn = yield_l * (day_kwh * daylight_fraction + night_used)
    fuel_use_nlph = fuel_kw / fuel_kwh_per_litre if hour >= 12 else 0
    stored_h2_nl = 240 + 2 * oxygen_since_dawn - night_hours * fuel_kw / fuel_kwh_per_litre
    battery_kwh = .15 * battery_capacity + swing * (1 - daylight_fraction)
    battery_kwh += min(swing, max(0, fuel_kw * night_hours - night_used))
    # Count prior operating days by season so the water level carries over at dawn.
    from datetime import date
    from calendar import isleap
    before_year = dawn.year - 1
    leap_days = before_year//4 - before_year//100 + before_year//400
    cold_days = 120 * before_year + leap_days
    cold_days += sum((date(dawn.year, m+1, 1)-date(dawn.year,m,1)).days
                     for m in (1,2,11) if m < dawn.month)
    if cold:
        cold_days += dawn.day - 1
    warm_days = dawn.toordinal() - 1 - cold_days
    def daily_kwh(factor, support):
        peak = min(rated, model['rated_solar_w']/1000 * factor + support/sun_hours)
        return peak * sun_hours + night_kwh
    lifetime_o2 = oxygen_since_dawn + yield_l * (cold_days*daily_kwh(.65,5.6) + warm_days*daily_kwh(1,2.8))
    water_used = lifetime_o2 * 2 * WATER_MOLAR_MASS_G / O2_MOLAR_VOLUME_L / 1000
    water_pct = 100 * (1 - water_used % (.9 * model['water_tank_l']) / model['water_tank_l'])
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
        'battery_pct': round(100*battery_kwh/battery_capacity,1),
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
