from datetime import datetime
from app.models import Tree
from app.catalog import get_model
from app.urban_history import urban_sample


def test_urban_ratings_at_solar_noon():
    for serial, kw, oxygen, water, hydrogen in [
        ('SOLIX-ARC-0001', 2, 250, 10, 20),
        ('SOLIX-HALO-0002', 5, 625, 40, 40),
    ]:
        tree = Tree(id=1, code=serial, model_code='ST-URBAN-2KW')
        model = get_model(tree.model_code, serial)
        assert (model['water_tank_l'], model['hydrogen_tank_l']) == (water, hydrogen)
        reading, _ = urban_sample(tree, datetime(2026, 6, 1, 11))
        assert model['oxygen_nominal_lph'] == oxygen
        assert 0 < reading.oxygen_flow_lph <= oxygen
        assert 0 < reading.electrolyzer_power_w <= kw * 1000
        assert model['fuel_cell_kw'] == (1.5 if serial.endswith('0002') else 1)
