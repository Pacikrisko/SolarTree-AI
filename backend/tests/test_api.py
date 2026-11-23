"""SolarTree AI v0.3 integration tests (local test database, never production data)."""
import os
from pathlib import Path
DB=Path(__file__).resolve().parents[1]/'solartree_test_v03.db'
if DB.exists(): DB.unlink()
os.environ['DATABASE_URL']='sqlite:///'+str(DB)
os.environ['DEMO_MODE']='true'
os.environ['OPENAI_API_KEY']=''
from fastapi.testclient import TestClient
from app.main import app


def auth(c,email='owner@demo.bg',password='Demo12345!'):
    r=c.post('/api/auth/login',json={'email':email,'password':password})
    assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['access_token']}


def pair(kind):
    if kind=='private':return {'code':'ST-M6-1001','claim_token':'DEMO-PRIVATE-PAIR-2026'}
    return {'code':'ST-M8-2001','claim_token':'DEMO-MUNICIPAL-PAIR-2026'}


def test_role_isolation_and_automatic_models():
    with TestClient(app) as c:
        own=auth(c)
        city=auth(c,'municipality@demo.bg')
        assert c.get('/api/trees').status_code==401
        mine=c.get('/api/trees',headers=own).json()
        their=c.get('/api/trees',headers=city).json()
        assert len(mine)==1 and mine[0]['model']['panel_count']==6
        assert len(their)==3 and all(t['model']['panel_count']==8 for t in their)
        own_id=mine[0]['id']; city_id=their[0]['id']
        for url in [f'/api/trees/{city_id}', f'/api/trees/{city_id}/config',
                    f'/api/trees/{city_id}/readings',f'/api/trees/{city_id}/oxygen',
                    f'/api/trees/{city_id}/forecast']:
            assert c.get(url,headers=own).status_code==404,url
        assert c.get(f'/api/trees/{own_id}',headers=city).status_code==404
        assert c.put(f'/api/trees/{own_id}/config',headers=own,json={'panel_count':9,'tilt_deg':0}).status_code==405
        assert c.post('/api/chat',headers=own,json={'tree_id':city_id,'message':'Hello'}).status_code==404


def test_qr_claim_and_permissions():
    with TestClient(app) as c:
        own=auth(c);city=auth(c,'municipality@demo.bg')
        private=pair('private')
        assert c.post('/api/pair/resolve',headers=city,json=private).status_code==403
        assert c.post('/api/pair/resolve',headers=own,json={'code':private['code'],'claim_token':'wrong-secret-key-value'}).status_code==404
        r=c.post('/api/pair/resolve',headers=own,json=private)
        assert r.status_code==200 and r.json()['model']['code']=='ST-M6'
        payload={**private,'name':'Соларно дърво в дома','location':'Частна локация','lat':None,'lng':None}
        assert c.post('/api/trees',headers=city,json=payload).status_code==403
        r=c.post('/api/trees',headers=own,json=payload)
        assert r.status_code==201,r.text
        t=r.json();assert t['model']['panel_count']==6 and t['kind']=='private'
        assert c.post('/api/trees',headers=own,json=payload).status_code==409
        assert c.post('/api/pair/resolve',headers=own,json=private).status_code==409
        assert c.get(f'/api/trees/{t["id"]}',headers=city).status_code==404
        url=f'/api/trees/{t["id"]}'
        assert c.delete(url).status_code==401
        assert c.delete(url,headers=city).status_code==404
        assert c.delete(url,headers=own).status_code==200
        assert all(row['id']!=t['id'] for row in c.get('/api/trees',headers=own).json())
        assert c.get(url+'/readings',headers=own).status_code==404
        assert c.delete(url,headers=own).status_code==404
        again=c.post('/api/trees',headers=own,json=payload)
        assert again.status_code==201 and again.json()['id']!=t['id']
        # municipal QR can only be claimed from municipality account
        municipal=pair('municipal')
        assert c.post('/api/pair/resolve',headers=own,json=municipal).status_code==403
        assert c.post('/api/pair/resolve',headers=city,json=municipal).json()['model']['panel_count']==8


def test_oxygen_graph_and_device_ingestion():
    with TestClient(app) as c:
        own=auth(c)
        my_tree=c.get('/api/trees',headers=own).json()[0]
        sample=c.get(f'/api/trees/{my_tree["id"]}/oxygen',headers=own).json()
        assert sample['total_l']>0 and sample['basis']=='simulation'
        assert sample['points'] and sample['points'][-1]['source']=='simulation'
        unclaimed=pair('private')
        # from prior test the same DB is used; registered new physical tree already exists
        r=c.post('/api/device/ST-M6-1001/reading',headers={'X-Device-Key':'incorrect'},json={
            'power_w':800,'temperature_c':20,'humidity_pct':40,'h2_sensor_value':.1,'water_pct':80,
            'oxygen_flow_lph':70.5,'electrolyzer_power_w':500})
        assert r.status_code==401
        token='DEMO-PRIVATE-DEVICE-KEY-2026'
        payload={'power_w':800,'temperature_c':20,'humidity_pct':40,'h2_sensor_value':.1,'water_pct':80,
                 'oxygen_flow_lph':70.5,'electrolyzer_power_w':500}
        r=c.post('/api/device/ST-M6-1001/reading',headers={'X-Device-Key':token},json=payload)
        assert r.status_code==200,r.text
        assert r.json()['reading']['oxygen_basis']=='measured'
        latest=c.get('/api/trees',headers=own).json()
        device=next(x for x in latest if x['code']=='ST-M6-1001')
        assert device['latest']['oxygen_flow_lph']==70.5
        assert device['connection']=='live'
        oxygen=c.get(f'/api/trees/{device["id"]}/oxygen',headers=own).json()
        assert oxygen['basis']=='measured' and oxygen['current_flow_lph']==70.5


def test_profile_update_and_password():
    with TestClient(app) as c:
        h=auth(c)
        r=c.patch('/api/auth/me',headers=h,json={'name':'Собственик SolarTree'})
        assert r.status_code==200 and r.json()['name']=='Собственик SolarTree'
        assert c.post('/api/auth/change-password',headers=h,json={'current_password':'wrong-password','new_password':'AsecurePassword2026'}).status_code==403
        r=c.post('/api/auth/change-password',headers=h,json={'current_password':'Demo12345!','new_password':'AsecurePassword2026'})
        assert r.status_code==200
        assert c.post('/api/auth/login',json={'email':'owner@demo.bg','password':'Demo12345!'}).status_code==401
        assert c.post('/api/auth/login',json={'email':'owner@demo.bg','password':'AsecurePassword2026'}).status_code==200


def test_forecast_services_ai_route():
    with TestClient(app) as c:
        city=auth(c,'municipality@demo.bg')
        tree=c.get('/api/trees',headers=city).json()[0]
        f=c.get(f'/api/trees/{tree["id"]}/forecast',headers=city)
        assert f.status_code==200 and len(f.json()['points'])==6
        assert len(c.get('/api/maintenance',headers=city).json())>=6
        assert c.post('/api/chat',headers=city,json={'tree_id':tree['id'],'message':'How is the tree?'}).status_code==503


def test_existing_sqlite_data_migrates_without_deletion(tmp_path):
    from sqlalchemy import create_engine, text
    from app.migrations import upgrade
    path=tmp_path/'old_02.db'
    e=create_engine(f'sqlite:///{path}')
    with e.begin() as c:
        c.exec_driver_sql('CREATE TABLE trees (id INTEGER PRIMARY KEY, kind VARCHAR(20), code VARCHAR(40))')
        c.exec_driver_sql('CREATE TABLE readings (id INTEGER PRIMARY KEY, source VARCHAR(20), power_w FLOAT)')
        c.exec_driver_sql("INSERT INTO trees (id,kind,code) VALUES (1,'municipal','STZ-001')")
        c.exec_driver_sql("INSERT INTO readings (id,source,power_w) VALUES (1,'simulation',1000)")
    upgrade(e)
    with e.connect() as c:
        assert c.execute(text('SELECT model_code FROM trees WHERE id=1')).scalar()=='ST-M8'
        row=c.execute(text('SELECT oxygen_flow_lph,oxygen_basis FROM readings WHERE id=1')).one()
        assert row[0]==65.0 and row[1]=='simulation'
        assert c.execute(text('SELECT COUNT(*) FROM trees')).scalar()==1
    e.dispose()


def test_service_only_media_and_owner_scope():
    with TestClient(app) as c:
        try: own=auth(c,'owner@demo.bg','AsecurePassword2026')
        except AssertionError: own=auth(c,'owner@demo.bg','Demo12345!')
        city=auth(c,'municipality@demo.bg')
        tid=c.get('/api/trees',headers=own).json()[0]['id']
        url=f'/api/trees/{tid}/media'
        assert c.get(url,headers=city).status_code==404
        assert c.post(url,headers=own,files={'file':('hi.png',b'data','image/png')}).status_code==403
        assert c.delete(url,headers=own).status_code==403
        assert c.get(url,headers=own).status_code==404  # M6 has no service image


def test_mobile_phone_pairing_and_real_pico_sensors(monkeypatch):
    monkeypatch.setenv('PUBLIC_SCANNER_URL','https://scanner.example.test')
    with TestClient(app) as c:
        try: own=auth(c,'owner@demo.bg','AsecurePassword2026')
        except AssertionError: own=auth(c,'owner@demo.bg','Demo12345!')
        city=auth(c,'municipality@demo.bg')
        r=c.post('/api/pair-sessions',headers=own)
        assert r.status_code==200,r.text
        info=r.json()
        assert info['url'].startswith('https://scanner.example.test/scan/')
        assert info['qr_data_uri'].startswith('data:image/png;base64,')
        token=info['url'].split('/')[-1]
        assert c.get('/scan/'+token).status_code==200
        assert c.get(f'/api/pair-sessions/{info["id"]}',headers=city).status_code==404
        bad=c.post('/api/scan/'+token,json={'payload':'STREE1|IVAN-TREE-0001|BAD-KEY-123456789'})
        assert bad.status_code==404
        r=c.post('/api/scan/'+token,json={'payload':'STREE1|IVAN-TREE-0001|IVAN-PROTOTYPE-PAIR-2026'})
        assert r.status_code==200,r.text
        state=c.get(f'/api/pair-sessions/{info["id"]}',headers=own).json()
        assert state['status']=='completed' and state['tree_id']
        tid=state['tree_id']
        assert c.get('/scan/'+token).status_code==410
        assert c.get(f'/api/trees/{tid}',headers=city).status_code==404
        asset=c.get(f'/api/trees/{tid}/media',headers=own)
        assert asset.status_code==200 and asset.headers['content-type'].startswith('image/jpeg')
        assert c.post('/api/device/IVAN-TREE-0001/sensors',headers={'X-Device-Key':'wrong'},json={'mq8_adc_raw':24900}).status_code==401
        recorded=c.post('/api/device/IVAN-TREE-0001/sensors',headers={'X-Device-Key':'IVAN-PROTOTYPE-DEVICE-KEY-2026'},json={
            'temperature_c':24.1,'humidity_pct':41.2,'mq8_adc_raw':20000})
        assert recorded.status_code==200,recorded.text
        tree=c.get(f'/api/trees/{tid}',headers=own).json()
        assert tree['connection']=='live' and tree['latest_sensors']['mq8_adc_raw']==20000
        assert tree['latest'] is None  # no invented power or O2 readings


def test_urban_qr_only_and_resource_calculator(monkeypatch):
    from app.resource_math import resource_estimate
    with TestClient(app) as c:
        try: own=auth(c,'owner@demo.bg','AsecurePassword2026')
        except AssertionError: own=auth(c,'owner@demo.bg','Demo12345!')
        city=auth(c,'municipality@demo.bg')
        # Switch off all global demo actions before pairing this reserved serial.
        monkeypatch.setattr('app.main.DEMO_MODE', False)
        assert c.post('/api/examples/urban',headers=own).status_code==404
        r=c.post('/api/pair/resolve',headers=own,json={
            'code':'URBAN-TREE-0001','claim_token':'URBAN-2KW-PAIR-2026'})
        assert r.status_code==200,r.text
        model=r.json()['model']
        assert model['electrolyzer_kw']==2 and model['oxygen_nominal_lph']==250
        assert model['fuel_cell_kw']==1
        assert model['hydrogen_tank_l']==20 and model['water_tank_l']==10
        r=c.post('/api/trees',headers=own,json={
            'code':'URBAN-TREE-0001','claim_token':'URBAN-2KW-PAIR-2026',
            'name':'SolarTree Urban 2K','location':'Тестова зона','lat':None,'lng':None})
        assert r.status_code==201,r.text
        tid=r.json()['id']
        assert r.json()['latest']['source']=='simulation'
        detail = c.get(f'/api/trees/{tid}',headers=own).json()
        assert detail['connection']=='model' and detail['latest_sensors'] is None
        operating = detail['simulation']
        assert 0 < operating['hydrogen_pressure_bar_g'] < 500 and 0 < operating['fuel_cell_load_kw'] <= 1
        history = c.get(f'/api/trees/{tid}/readings',headers=own).json()
        assert len(history)==96 and all(r['source']=='simulation' for r in history)
        assert history==sorted(history, key=lambda row:row['time'])
        assert all(r['electrolyzer_power_w'] is not None for r in history)
        assert c.get(f'/api/trees/{tid}/forecast',headers=own).json()['synthetic_data']
        assert c.get(f'/api/trees/{tid}/readings',headers=city).status_code==404
        assert c.post(f'/api/trees/{tid}/simulate',headers=own,json={'mode':'normal'}).status_code==403
        with_params = c.get(f'/api/trees/{tid}/resources',headers=own,params={
            'water_fill_pct':detail['latest']['water_pct'],
            'pressure_bar_g':operating['hydrogen_pressure_bar_g'],
            'fuel_cell_load_kw':operating['fuel_cell_load_kw']}).json()
        assert with_params['hydrogen_runtime_hours'] > 0 and with_params['water_runtime_hours'] > 0
        assert c.get(f'/api/trees/{tid}/oxygen',headers=own).json()['basis']=='simulation'
        assert c.post('/api/trees',headers=own,json={
            'code':'URBAN-TREE-0001','claim_token':'URBAN-2KW-PAIR-2026',
            'name':'Дубликат','location':'Тест','lat':None,'lng':None}).status_code==409
        assert c.get(f'/api/trees/{tid}/resources',headers=city).status_code==404
        r=c.get(f'/api/trees/{tid}/resources',headers=own)
        assert r.status_code==200,r.text
        value=r.json()
        assert value['hydrogen_runtime_hours'] is None
        assert value['hydrogen_usable_normal_l'] is None
        assert 24 < value['water_runtime_hours'] < 26
        assert 0.39 < value['water_consumption_lph'] < 0.42
        r=c.get(f'/api/trees/{tid}/resources',headers=own,params={
            'water_fill_pct':40,'pressure_bar_g':10,'fuel_cell_load_kw':1,'efficiency':0.5})
        assert r.status_code==200,r.text
        value=r.json()
        assert value['water_available_l']==4
        assert 9 < value['water_runtime_hours'] < 11
        assert 180 < value['hydrogen_usable_normal_l'] < 190
        assert 0.26 < value['hydrogen_runtime_hours'] < 0.29
        assert value['fuel_cell_hydrogen_consumption_nlph']>660
        assert c.get(f'/api/trees/{tid}/resources',headers=own,params={
            'pressure_bar_g':-1}).status_code==422
        assert c.get(f'/api/trees/{tid}/media',headers=own).status_code==200
        assert c.get(f'/api/trees/{tid}/resources',headers=own,params={
            'fuel_cell_load_kw':2}).status_code==422
        owner_tree=next(x for x in c.get('/api/trees',headers=own).json() if x['model']['code']=='ST-M6')
        assert c.get(f'/api/trees/{owner_tree["id"]}/resources',headers=own).status_code==404
    physical=resource_estimate(water_capacity_l=10,hydrogen_tank_internal_l=20,
                               oxygen_nominal_nlph=250,fuel_cell_power_kw=1,pressure_bar_g=10)
    assert 16 < physical['hydrogen_runtime_hours']*60 < 18


def test_new_account_registration_and_duplicate_email():
    """Registration regression: user creation is an API path, not just login."""
    with TestClient(app) as client:
        payload = {'name': 'Тестов собственик', 'email': 'new.account.v071@example.org', 'password': 'StrongTestPass23!'}
        result = client.post('/api/auth/register', json=payload)
        assert result.status_code == 201, result.text
        body = result.json()
        assert body['user']['role'] == 'owner'
        assert body['user']['email'] == payload['email']
        assert body['access_token']
        auth = {'Authorization': 'Bearer ' + body['access_token']}
        assert client.get('/api/auth/me', headers=auth).status_code == 200
        assert client.post('/api/auth/register', json=payload).status_code == 409
        assert client.post('/api/auth/register', json={**payload, 'email': 'not-an-email'}).status_code == 422


def test_urban_simulation_minute_updates_and_day_night_cycle():
    from datetime import datetime, timedelta
    from app.models import Tree
    from app.urban_history import is_urban_simulator, urban_readings, urban_sample

    tree = Tree(id=9, code='URBAN-TREE-0001', model_code='ST-URBAN-2KW')
    assert is_urban_simulator(tree)
    for code, model in [('IVAN-TREE-0001', 'ST-IVAN-P1'), ('OTHER-2K', 'ST-URBAN-2KW')]:
        assert not is_urban_simulator(Tree(code=code, model_code=model))
    morning = datetime(2026, 11, 23, 8, 0)
    rows = urban_readings(tree, 96, morning)
    next_rows = urban_readings(tree, 96, morning + timedelta(minutes=1))
    assert next_rows[1].time == rows[0].time
    assert next_rows[1].power_w == rows[0].power_w
    assert next_rows[0].power_w > rows[0].power_w
    day, gas_day = urban_sample(tree, morning + timedelta(hours=3))
    night, gas_night = urban_sample(tree, morning + timedelta(hours=15))
    assert 0 < day.electrolyzer_power_w <= 2000 and day.electrolyzer_power_w <= day.power_w <= 3200
    assert night.power_w == night.electrolyzer_power_w == night.oxygen_flow_lph == 0
    assert gas_day['hydrogen_flow_nlph'] == 2 * day.oxygen_flow_lph
    assert gas_night['fuel_cell_load_kw'] > 0 and 0 < night.water_pct < day.water_pct <= 100
