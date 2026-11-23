"""Manufacturer/service-controlled model catalogue. No end-user media changes."""
MODELS = {
    'ST-M6': {'code': 'ST-M6', 'name': 'SolarTree Compact M6', 'panel_count': 6, 'tilt_deg': 16,
              'rated_solar_w': 800, 'description': 'Компактен модел с шест панела'},
    'ST-M8': {'code': 'ST-M8', 'name': 'SolarTree Urban M8', 'panel_count': 8, 'tilt_deg': 16,
              'rated_solar_w': 1500, 'description': 'Общински модел с осем панела'},
    'ST-IVAN-P1': {'code': 'ST-IVAN-P1', 'name': 'SolarTree Prototype P1', 'panel_count': 6, 'tilt_deg': 14,
                   'rated_solar_w': 16, 'description': 'Физическият прототип на соларното дърво; свързване чрез Raspberry Pi Pico 2 W'},
    'ST-URBAN-2KW': {'code': 'ST-URBAN-2KW', 'name': 'SolarTree Urban 2K', 'panel_count': 8, 'tilt_deg': 15,
                 'rated_solar_w': 3200, 'electrolyzer_kw': 2, 'oxygen_nominal_lph': 250, 'fuel_cell_kw': 1, 'water_tank_l': 10.0, 'hydrogen_tank_l': 20.0,
                 'description': 'Пълноразмерен проект: електролизер 2 kW, O₂ 250 Nl/h (проектно), горивна клетка 1 kW; вода 10 L; съд за водород 20 L (вътрешен обем)'},
}

def get_model(code: str | None) -> dict:
    return MODELS.get(code or '', MODELS['ST-M6'])
