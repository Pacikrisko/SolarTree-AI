"""Advisory calculation only. Never controls gas pressure or the fuel cell.
Standard reference: 0 C, 1.01325 bar, ideal gas approximation; gas molar volume 22.414 L/mol.
"""
from math import isfinite

O2_MOLAR_VOLUME_L = 22.414
WATER_MOLAR_MASS_G = 18.01528
WATER_DENSITY_KG_PER_L = 1.0  # approximation
NORMAL_PRESSURE_BAR = 1.01325
NORMAL_TEMP_K = 273.15
TANK_TEMP_K = 293.15  # nominal reference 20 C; NOT a temperature sensor
H2_LHV_KWH_PER_NORMAL_M3 = 3.0


def resource_estimate(*, water_capacity_l: float, hydrogen_tank_internal_l: float,
                      oxygen_nominal_nlph: float, fuel_cell_power_kw: float,
                      water_fill_pct: float = 100.0, pressure_bar_g: float | None = None,
                      fuel_cell_load_kw: float | None = None, fuel_cell_efficiency: float = 0.50):
    """Water depletes only while producing O2 at the stated flow.
    Fuel cell capacity requires actual hydrogen pressure; when unknown return None.
    Gauge pressure relative to approx 1 bar; usable gas down to 0 bar(g).
    """
    if not all(isfinite(x) and x >= 0 for x in
               (water_capacity_l, hydrogen_tank_internal_l, oxygen_nominal_nlph, fuel_cell_power_kw)):
        raise ValueError('Invalid rated values')
    if not 0 <= water_fill_pct <= 100:
        raise ValueError('water_fill_pct out of range')
    if pressure_bar_g is not None and (not isfinite(pressure_bar_g) or not 0 <= pressure_bar_g <= 500):
        raise ValueError('pressure_bar_g out of range')
    load_kw = fuel_cell_power_kw if fuel_cell_load_kw is None else fuel_cell_load_kw
    if not isfinite(load_kw) or not 0 <= load_kw <= fuel_cell_power_kw:
        raise ValueError('fuel_cell_load_kw out of range')
    if not 0 < fuel_cell_efficiency <= 1:
        raise ValueError('fuel_cell_efficiency out of range')
    # 2 H2O => 2 H2 + O2: two mol water per mol O2.
    water_lph = oxygen_nominal_nlph / O2_MOLAR_VOLUME_L * 2 * WATER_MOLAR_MASS_G / 1000 / WATER_DENSITY_KG_PER_L
    water_available_l = water_capacity_l * water_fill_pct / 100
    water_hours = water_available_l / water_lph if water_lph > 0 else None
    # In Normal liters at 0 C, 1.01325 bar: isothermal approximation using nominal 20 C cylinder temperature.
    hydrogen_usable_nl = (hydrogen_tank_internal_l * pressure_bar_g / NORMAL_PRESSURE_BAR * NORMAL_TEMP_K / TANK_TEMP_K
                          if pressure_bar_g is not None else None)
    h2_nlph = (load_kw / (fuel_cell_efficiency * H2_LHV_KWH_PER_NORMAL_M3) * 1000
               if load_kw > 0 else 0.0)
    hydrogen_hours = ((hydrogen_usable_nl / h2_nlph) if hydrogen_usable_nl is not None and h2_nlph > 0 else None)
    return {
        'water_capacity_l': water_capacity_l,
        'water_fill_pct': water_fill_pct,
        'water_available_l': round(water_available_l, 3),
        'water_consumption_lph': round(water_lph, 4),
        'water_runtime_hours': round(water_hours, 3) if water_hours is not None else None,
        'hydrogen_tank_internal_l': hydrogen_tank_internal_l,
        'hydrogen_pressure_bar_g': pressure_bar_g,
        'hydrogen_usable_normal_l': round(hydrogen_usable_nl, 2) if hydrogen_usable_nl is not None else None,
        'fuel_cell_load_kw': load_kw,
        'fuel_cell_efficiency': fuel_cell_efficiency,
        'fuel_cell_hydrogen_consumption_nlph': round(h2_nlph, 2),
        'hydrogen_runtime_hours': round(hydrogen_hours, 3) if hydrogen_hours is not None else None,
        'standard_conditions': '0 °C, 1.01325 bar; tank model assumes 20 °C, ideal gas and depletion to 0 bar(g)',
        'basis': 'engineering_estimate_not_sensor_data',
    }
