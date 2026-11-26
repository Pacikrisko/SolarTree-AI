"""Reproducible illustrative estimates for completed calendar months."""
from calendar import monthrange
from datetime import date
from hashlib import sha256
from math import cos, pi
from .catalog import get_model


def archive_months(today=None):
    today = today or date.today()
    index = today.year * 12 + today.month - 1
    months = []
    for offset in range(1, 13):
        year, month = divmod(index - offset, 12)
        months.append(f'{year:04d}-{month + 1:02d}')
    return months


def monthly_archive(tree, month):
    year, number = map(int, month.split('-'))
    model = get_model(tree.model_code, tree.code)
    sun_hours = 4.2 + 2.0 * cos((number - 6) * pi / 6)
    power_kw = model['rated_solar_w'] / 1000
    oxygen_rate = model.get('oxygen_nominal_lph', power_kw * 125)
    days = []
    for day in range(1, monthrange(year, number)[1] + 1):
        stamp = f'{month}-{day:02d}'
        variation = sha256(f'{tree.code}/{stamp}'.encode()).digest()[0] / 255
        hours = sun_hours * (0.50 + 0.65 * variation)
        days.append(dict(date=stamp, energy_kwh=round(power_kw * hours, 3),
                         oxygen_l=round(oxygen_rate * hours, 1)))
    return dict(month=month, basis='illustrative_estimate', days=days,
                energy_kwh=round(sum(d['energy_kwh'] for d in days), 3),
                oxygen_l=round(sum(d['oxygen_l'] for d in days), 1),
                peak_oxygen_day=max(days, key=lambda d: d['oxygen_l'])['date'])
