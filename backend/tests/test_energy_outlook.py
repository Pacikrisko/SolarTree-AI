from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.energy_outlook import energy_outlook
from app.models import Reading, Tree


def test_five_day_urban_forecast_follows_its_daylight_cycle():
    now = datetime(2026, 11, 24, 23, tzinfo=timezone.utc)
    tree = Tree(id=1, name='Centere', code='URBAN-TREE-0001', model_code='ST-URBAN-2KW')
    result = energy_outlook(None, tree, 'simulation', now)
    assert result['basis'] == 'repeating Urban simulation'
    assert result['first_full_day_utc'] == '2026-11-25'
    assert result['kwh_each_day'] == pytest.approx(24.4462, abs=.0001)
    assert result['total_kwh_by_number_of_days']['5'] == pytest.approx(122.231, abs=.001)
    assert not result['weather_adjusted']


def test_complete_days_are_weighted_by_time_and_scoped_to_tree_and_source():
    now = datetime(2026, 11, 24, 12, tzinfo=timezone.utc)
    tree = Tree(id=2, code='prototype', model_code='ST-IVAN-P1')
    engine = create_engine('sqlite://')
    Reading.__table__.create(engine)
    with Session(engine) as db:
        def add(tree_id, source, start, count, power):
            for i in range(count):
                db.add(Reading(tree_id=tree_id, time=start+timedelta(minutes=i*15), power_w=power,
                               source=source, temperature_c=20, humidity_pct=40, water_pct=80, h2_sensor_value=0))
        start = datetime(2026, 11, 22)
        add(2, 'device', start, 96, 10)
        add(2, 'device', start+timedelta(days=1), 95, 14)
        add(2, 'simulation', start, 96, 200)
        add(3, 'device', start, 96, 1000)
        result = energy_outlook(db, tree, 'device', now)
        assert result['complete_days'] == 1
        assert result['history_source'] == 'device'
        assert result['total_kwh_by_number_of_days']['5'] == 1.2
        stale = energy_outlook(db, tree, 'device', now+timedelta(days=10))
        assert 'scenario' in stale['basis']
        assert stale['assumed_equivalent_full_power_hours_per_day'] == 4
        assert stale['total_kwh_by_number_of_days']['5'] == 16 * 4 * 5 / 1000
