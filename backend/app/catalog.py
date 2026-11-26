"""Manufacturer/service-controlled model catalogue. No end-user media changes."""
MODELS = {
    'ST-M6': {'code': 'ST-M6', 'name': 'Solix Compact M6', 'panel_count': 6, 'tilt_deg': 16,
              'rated_solar_w': 800, 'description': 'Компактен модел с шест панела'},
    'ST-M8': {'code': 'ST-M8', 'name': 'Solix Municipal M8', 'panel_count': 8, 'tilt_deg': 16,
              'rated_solar_w': 1500, 'description': 'Общински модел с осем панела'},
    'ST-IVAN-P1': {'code': 'ST-IVAN-P1', 'name': 'Solix Prototype P1', 'panel_count': 6, 'tilt_deg': 14,
                   'rated_solar_w': 16, 'description': 'Физическият прототип на соларното дърво; свързване чрез Raspberry Pi Pico 2 W'},
    'ST-URBAN-2KW': {'code': 'ST-URBAN-2KW', 'name': 'Solix Arc 2K', 'panel_count': 8, 'tilt_deg': 15,
                 'rated_solar_w': 3200, 'electrolyzer_kw': 2, 'oxygen_nominal_lph': 250, 'fuel_cell_kw': 1, 'water_tank_l': 10.0, 'hydrogen_tank_l': 20.0,
                 'description': 'Пълноразмерен проект: електролизер 2 kW, O₂ 250 Nl/h (проектно), горивна клетка 1 kW; вода 10 L; съд за водород 20 L (вътрешен обем)'},
}

def get_model(code: str | None, serial: str | None = None) -> dict:
    if code == 'ST-URBAN-2KW' and serial == 'SOLIX-HALO-0002':
        return {**MODELS[code], 'name':'Solix Halo 5K', 'electrolyzer_kw':5, 'fuel_cell_kw':1.5,
                'oxygen_nominal_lph':625, 'water_tank_l':40, 'hydrogen_tank_l':40,
                'description':'Електролизер 5 kW, кислород 625 L/h, вода 40 L и водороден съд 40 L.'}
    if serial == 'SOLIX-ARC-0001' and code == 'ST-URBAN-2KW':
        return {**MODELS[code], 'auxiliary_kw':1}
    return MODELS.get(code or '', MODELS['ST-M6'])
