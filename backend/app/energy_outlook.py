"""Account chat inputs for multi-day electricity estimates (PV output in kWh)."""
import math
from datetime import timedelta

from sqlalchemy import Integer, cast, extract, func, select

from .catalog import get_model
from .models import Reading
from .urban_history import is_urban_simulator, URBAN_DAYLIGHT_HOURS, winter_solar_factor


def recent_daily_energy(db, tree_id, source, midnight):
    # Weight equal time intervals equally even when telemetry arrives in bursts.
    day = func.date(Reading.time)
    hour = extract('hour', Reading.time)
    quarter = cast(extract('minute', Reading.time), Integer).op('/')(15)
    bins = (select(day.label('day'), func.avg(Reading.power_w).label('watts'))
            .where(Reading.tree_id == tree_id, Reading.source == source,
                   Reading.time >= midnight - timedelta(days=7), Reading.time < midnight)
            .group_by(day, hour, quarter).subquery())
    return db.execute(select(bins.c.day, (func.sum(bins.c.watts) / 4000).label('kwh'))
                      .group_by(bins.c.day).having(func.count() == 96).order_by(bins.c.day)).all()


def energy_outlook(db, tree, source, now):
    """Next full UTC days under a stated repeat-day assumption, without weather input."""
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    rating = get_model(tree.model_code, tree.code)['rated_solar_w']
    details = {}
    totals = {}
    if is_urban_simulator(tree):
        # Integral of the simulator's sine curve from sunrise to sunset.
        daily = rating / 1000 * 2 * URBAN_DAYLIGHT_HOURS / math.pi
        nominal = daily
        accumulated = 0.
        for n in range(1, 15):
            accumulated += nominal * winter_solar_factor(midnight + timedelta(days=n))
            totals[str(n)] = round(accumulated, 4)
        daily = totals['1']
        basis = 'repeating Urban simulation'
    else:
        days = recent_daily_energy(db, tree.id, source, midnight) if source else []
        if days:
            daily = sum(float(row.kwh) for row in days) / len(days)
            basis = 'mean of recent complete UTC days'
            details = {'history_source': source, 'complete_days': len(days),
                       'last_complete_date': str(days[-1].day)}
        else:
            # Illustrative scenario only: equivalent full-power hours are an explicit
            # assumption, not the daylight duration or a local irradiance forecast.
            daily = rating / 1000 * 4
            basis = 'illustrative nameplate scenario only (insufficient recent full-day telemetry)'
            details = {'assumed_equivalent_full_power_hours_per_day': 4, 'rated_pv_w': rating}
    return {'basis': basis, **details, 'weather_adjusted': False,
            'first_full_day_utc': (midnight + timedelta(days=1)).date().isoformat(),
            'kwh_each_day': round(daily, 4),
            'total_kwh_by_number_of_days': totals or {str(n): round(n*daily, 4) for n in range(1, 15)}}
