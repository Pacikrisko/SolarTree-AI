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


def test_qr_claim_and_permissions(monkeypatch):
    monkeypatch.setenv('PUBLIC_SCANNER_URL','https://scanner.example.test')
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
        other=c.post('/api/auth/register',json={'name':'Друг собственик','email':'owner2@example.org','password':'SamplePass1234'}).json()
        second={'Authorization':'Bearer '+other['access_token']}
        assert c.post('/api/trees',headers=second,json=payload).status_code==201
        assert c.delete(f"/api/trees/{t['id']}",headers=second).status_code==200
        url=f'/api/trees/{t["id"]}'
        assert c.delete(url).status_code==401
        assert c.delete(url,headers=city).status_code==404
        assert c.delete(url,headers=own).status_code==200
        assert all(row['id']!=t['id'] for row in c.get('/api/trees',headers=own).json())
        assert c.get(url+'/readings',headers=own).status_code==404
        assert c.delete(url,headers=own).status_code==404
        assert c.post('/api/pair/resolve',headers=second,json=private).status_code==409
        assert c.post('/api/trees',headers=second,json=payload).status_code==409
        phone=c.post('/api/pair-sessions',headers=second).json()['url'].split('/')[-1]
        scan='STREE1|'+private['code']+'|'+private['claim_token']
        assert c.post('/api/scan/'+phone,json={'payload':scan}).status_code==409
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
        assert f.status_code==200 and len(f.json()['points'])==24
        from datetime import datetime, timedelta
        times=[datetime.fromisoformat(point['time']) for point in f.json()['points']]
        assert all(at.minute==0 for at in times)
        assert all(b-a==timedelta(hours=1) for a,b in zip(times,times[1:]))
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
            'code':'SOLIX-ARC-0001','claim_token':'URBAN-2KW-PAIR-2026'})
        assert r.status_code==200,r.text
        model=r.json()['model']
        assert model['electrolyzer_kw']==2 and model['oxygen_nominal_lph']==250
        assert model['fuel_cell_kw']==1
        assert model['hydrogen_tank_l']==20 and model['water_tank_l']==10
        r=c.post('/api/trees',headers=own,json={
            'code':'SOLIX-ARC-0001','claim_token':'URBAN-2KW-PAIR-2026',
            'name':'SolarTree Urban 2K','location':'Тестова зона','lat':None,'lng':None})
        assert r.status_code==201,r.text
        tid=r.json()['id']
        assert r.json()['latest']['source']=='simulation'
        detail = c.get(f'/api/trees/{tid}',headers=own).json()
        assert detail['connection']=='model' and detail['latest_sensors'] is None
        operating = detail['simulation']
        assert 0 < operating['hydrogen_pressure_bar_g'] < 500 and 0 <= operating['fuel_cell_load_kw'] <= 1
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
        assert with_params['water_runtime_hours'] > 0
        assert c.get(f'/api/trees/{tid}/oxygen',headers=own).json()['basis']=='simulation'
        assert c.post('/api/trees',headers=own,json={
            'code':'SOLIX-ARC-0001','claim_token':'URBAN-2KW-PAIR-2026',
            'name':'Дубликат','location':'Тест','lat':None,'lng':None}).status_code==409
        assert c.get(f'/api/trees/{tid}/resources',headers=city).status_code==404
        r=c.get(f'/api/trees/{tid}/resources',headers=own)
        assert r.status_code==200,r.text
        value=r.json()
        assert value['hydrogen_usable_normal_l'] > 0
        assert value['water_runtime_hours'] > 0
        assert 0.39 < value['water_consumption_lph'] < 0.42
        r=c.get(f'/api/trees/{tid}/resources',headers=own,params={
            'water_fill_pct':40,'pressure_bar_g':10,'fuel_cell_load_kw':1,'efficiency':0.5})
        assert r.status_code==200,r.text
        assert abs(r.json()['water_available_l']-value['water_available_l']) < .1
        assert c.get(f'/api/trees/{tid}/resources',headers=own,params={
            'pressure_bar_g':-1}).status_code==422
        assert c.get(f'/api/trees/{tid}/media',headers=own).status_code==200
        assert c.get(f'/api/trees/{tid}/resources',headers=own,params={
            'fuel_cell_load_kw':2}).status_code==200
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

    tree = Tree(id=9, code='SOLIX-ARC-0001', model_code='ST-URBAN-2KW')
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
    assert night.power_w == 0 and 0 < night.oxygen_flow_lph < day.oxygen_flow_lph * .1
    assert 0 <= gas_night["battery_pct"] <= 100
    assert gas_day['hydrogen_flow_nlph'] == 2 * day.oxygen_flow_lph
    assert gas_night['fuel_cell_load_kw'] > 0 and 10 <= night.water_pct <= 100


def test_assistant_only_receives_authenticated_inventory(monkeypatch):
    with TestClient(app) as c:
        empty=c.post('/api/auth/register',json={'name':'Празен профил','email':'empty@example.org','password':'SamplePass1234'}).json()
        headers={'Authorization':'Bearer '+empty['access_token']}
        city=auth(c,'municipality@demo.bg')
        tree=c.get('/api/trees',headers=city).json()[0]
        assert c.post('/api/chat',json={'message':'Справка','report':'overview'}).status_code==401
        report=c.post('/api/chat',headers=city,json={'message':'Справка','report':'overview'})
        assert tree['code'] in report.json()['reply']
        assert c.post('/api/chat',headers=headers,json={'message':'Справка','report':'energy','tree_id':tree['id']}).status_code==404
        calls=[]
        def fake_answer(message,context,history):
            calls.append(context)
            return {'reply':'OK','mode':'llm','model':'test'}
        monkeypatch.setenv('OPENAI_API_KEY','test-only')
        monkeypatch.setattr('app.main.answer',fake_answer)
        assert c.post('/api/chat',headers=headers,json={'message':'Всички дървета'}).status_code==200
        assert calls[-1]['trees']==[]
        assert c.post('/api/chat',headers=headers,json={'message':'Детайли','tree_id':tree['id']}).status_code==404
        assert len(calls)==1
        assert c.post('/api/chat',headers=city,json={'message':'Детайли','tree_id':tree['id']}).status_code==200
        devices=calls[-1]['trees']
        assert [d['id'] for d in devices]==[tree['id']]
        assert devices[0]['maintenance'] and devices[0]['forecast']['points']


def test_cloudflare_chat_and_reports(monkeypatch):
    import httpx
    from app.assistant import CLOUDFLARE_MODEL
    monkeypatch.setenv('CLOUDFLARE_ACCOUNT_ID','a'*32)
    monkeypatch.setenv('CLOUDFLARE_API_TOKEN','test-only')
    requests=[]
    def post(url, *, headers, json, timeout):
        assert url.endswith('/'+'a'*32+'/ai/run/'+CLOUDFLARE_MODEL)
        assert headers['Authorization']=='Bearer test-only'
        assert json['messages'][0]['role']=='system'
        requests.append(json)
        return httpx.Response(200,json={'success':True,'result':{'response':'Тестов отговор'}})
    monkeypatch.setattr('app.assistant.httpx.post',post)
    with TestClient(app) as c:
        city=auth(c,'municipality@demo.bg')
        assert c.get('/api/health').json()['ai_provider']=='cloudflare'
        res=c.post('/api/chat',headers=city,json={'message':'Как работят дърветата?'})
        assert res.status_code==200 and res.json()['reply']=='Тестов отговор'
        assert len(requests)==1
        import json
        payload=json.loads(requests[0]['messages'][-1]['content'])
        assert payload['account_context']['trees']
        assert all('5' in tree['daily_energy_outlook']['total_kwh_by_number_of_days']
                   for tree in payload['account_context']['trees'])
        monkeypatch.setattr('app.assistant.httpx.post',lambda *a,**k:httpx.Response(429))
        assert c.post('/api/chat',headers=city,json={'message':'Въпрос'}).status_code==502
        assert c.post('/api/chat',headers=city,json={'message':'Справка','report':'overview'}).status_code==200
        monkeypatch.delenv('CLOUDFLARE_API_TOKEN')
        assert not c.get('/api/health').json()['real_llm']


def test_labels_checked_after_trimming():
    with TestClient(app) as c:
        payload={'name':'Test owner','email':'label-check@example.org','password':'SamplePass1234'}
        response=c.post('/api/auth/register',json=payload)
        assert response.is_success
        own={'Authorization':'Bearer '+response.json()['access_token']}
        assert c.patch('/api/auth/me',headers=own,json={'name':' x '}).status_code==422
        assert c.post('/api/auth/register',json={'name':'   ','email':'spaces@example.org','password':'SamplePass1234'}).status_code==422
        base={**pair('private'),'name':'Test tree','location':'Sofia'}
        for field in ('name','location'):
            assert c.post('/api/trees',headers=own,json={**base,field:'   '}).status_code==422


def test_energy_report_uses_latest_available_value_per_metric():
    from app.assistant import account_report
    device={'name':'Test','code':'test','connection':'live',
            'latest':{'time':'2026-10-01T10:00:00.100000Z','power_w':0,'water_pct':None},
            'latest_sensors':{'time':'2026-10-01T10:00:00Z','power_w':54,'water_pct':84}}
    report=account_report('energy',[device])
    assert 'Мощност: 0 W' in report and 'Вода: 84 %' in report and 'Кислород: няма данни' in report


def test_chat_history_is_persistent_private_and_paginated(monkeypatch):
    from uuid import uuid4
    def register(c,login):
        password='ChatHistoryTest123'
        account={'name':'History owner','email':login,'password':password}
        assert c.post('/api/auth/register',json=account).is_success
        return auth(c,login,password)

    with TestClient(app) as c:
        owner=register(c,'chat-history-a@example.org')
        other=register(c,'chat-history-b@example.org')
        assert c.get('/api/chat/history').status_code==401
        request={'message':'Status','report':'overview','language':'en','request_id':str(uuid4())}
        saved=c.post('/api/chat',headers=owner,json=request).json()
        assert saved['reply']=='There are no trees in this account.'
        assert c.post('/api/chat',headers=owner,json=request).json()['id']==saved['id']
        assert c.get('/api/chat/history',headers=other).json()['exchanges']==[]
        assert c.get('/api/chat/history',headers=owner).json()['exchanges']==[saved]
        monkeypatch.setenv('OPENAI_API_KEY','test-only')
        captured=[]
        def fake_reply(message,context,history):
            captured.append(history)
            return {'reply':'Test reply','mode':'llm','model':'test'}
        monkeypatch.setattr('app.main.answer',fake_reply)
        assert c.post('/api/chat',headers=owner,json={'message':'Follow-up'}).is_success
        assert [turn['content'] for turn in captured[-1]]==[saved['question'],saved['reply']]
        for i in range(30):
            assert c.post('/api/chat',headers=owner,json={'message':str(i),'report':'overview'}).is_success
        city=auth(c,'municipality@demo.bg')
        tree=c.get('/api/trees',headers=city).json()[0]['id']
        focused=c.post('/api/chat',headers=city,json={'message':'History scope','tree_id':tree,'report':'overview'}).json()
        assert focused in c.get('/api/chat/history',params={'tree_id':tree},headers=city).json()['exchanges']
        assert focused not in c.get('/api/chat/history',headers=city).json()['exchanges']
        assert c.get('/api/chat/history',params={'tree_id':tree},headers=other).status_code==404
    with TestClient(app) as second_device:
        auth_again=auth(second_device,'chat-history-a@example.org','ChatHistoryTest123')
        latest=second_device.get('/api/chat/history',headers=auth_again).json()
        assert len(latest['exchanges'])==30 and latest['has_more']
        older=second_device.get('/api/chat/history',params={'before':latest['exchanges'][0]['id']},headers=auth_again).json()
        assert len(older['exchanges'])==2 and not older['has_more']
        assert older['exchanges'][0]==saved


import pytest
from app import google_login



@pytest.fixture
def google(monkeypatch):
    monkeypatch.setenv('GOOGLE_CLIENT_ID','solartree-test.apps.googleusercontent.com')
    claims={'sub':'google-test-subject','email':'google-owner@example.org',
            'name':'Google User','email_verified':True}
    def verify(credential,transport,audience):
        assert audience=='solartree-test.apps.googleusercontent.com'
        if credential!='test-credential':
            raise ValueError('unverified')
        return claims.copy()
    monkeypatch.setattr(google_login.id_token,'verify_oauth2_token',verify)
    return claims


def sign_in(client,password=None,credential='test-credential'):
    return client.post('/api/auth/google',json={'credential':credential,'password':password},
                       headers={'X-Requested-With':'SolarTree'})


def test_google_sign_in_and_returning_identity(google):
    with TestClient(app) as c:
        assert c.get('/api/auth/google/config').json()['client_id']=='solartree-test.apps.googleusercontent.com'
        response=sign_in(c)
        assert response.status_code==200,response.text
        issued=response.json()
        user=issued['user']
        assert user['role']=='owner' and not user['has_password']
        bearer={'Authorization':'Bearer '+issued['access_token']}
        assert c.get('/api/auth/me',headers=bearer).json()==user
        assert c.post('/api/auth/login',json={'email':user['email'],'password':'irrelevant'}).status_code==401
        google['email']='updated-google@example.org'
        assert sign_in(c).json()['user']['id']==user['id']


def test_google_link_preserves_existing_account(google):
    google.update(sub='google-test-link',email='google-link@example.org')
    with TestClient(app) as c:
        account=c.post('/api/auth/register',json={'email':google['email'],'name':'Existing Owner','password':'TestPassword654'}).json()
        before={'Authorization':'Bearer '+account['access_token']}
        saved=c.post('/api/chat',headers=before,json={'message':'Status','report':'overview'}).json()
        assert sign_in(c).json()=={'requires_password':True,'email':google['email']}
        assert sign_in(c,'wrong password').status_code==403
        linked=sign_in(c,'TestPassword654').json()
        assert linked['user']==account['user']
        after={'Authorization':'Bearer '+linked['access_token']}
        assert saved in c.get('/api/chat/history',headers=after).json()['exchanges']
        assert sign_in(c).json()['user']==account['user']
        google['sub']='other-verified-google-account'
        assert sign_in(c,'TestPassword654').status_code==409


def test_google_verification_and_disabled_config(google,monkeypatch):
    with TestClient(app) as c:
        assert c.post('/api/auth/google',json={'credential':'test-credential'}).status_code==403
        assert sign_in(c,credential='not-verified').status_code==401
        google['email_verified']=False
        assert sign_in(c).status_code==403
        google['email_verified']=True
        google['sub']=''
        assert sign_in(c).status_code==403
        monkeypatch.delenv('GOOGLE_CLIENT_ID')
        assert c.get('/api/auth/google/config').json()=={'client_id':None}
        assert sign_in(c).status_code==503


def test_conversation_selection_context_and_deletion(monkeypatch):
    from uuid import uuid4
    with TestClient(app) as c:
        def account(email):
            password = 'PrivateChat123!'
            assert c.post('/api/auth/register', json={'name':'Chat tester','email':email,'password':password}).is_success
            return auth(c,email,password)
        owner = account('threads-owner@example.org')
        other = account('threads-other@example.org')
        def send(headers, title, thread=None, first=False):
            return c.post('/api/chat', headers=headers, json={'message':title,'report':'overview',
                          'request_id':thread if first else str(uuid4()),'conversation_id':thread})
        a, b = str(uuid4()), str(uuid4())
        assert send(owner,'Previous history').is_success
        assert send(owner,'Water',a,True).is_success
        assert send(owner,'Power',b,True).is_success
        assert send(other,'Independent history').is_success
        assert c.get('/api/chat/conversations',headers=owner).json()[2]['conversation_id'] is None
        captured = []
        monkeypatch.setenv('OPENAI_API_KEY','test-only')
        def answer(message,context,history):
            captured.extend(history)
            return {'reply':'Test reply','mode':'llm'}
        monkeypatch.setattr('app.main.answer',answer)
        assert c.post('/api/chat',headers=owner,json={'message':'Follow-up','conversation_id':a}).is_success
        assert [turn['content'] for turn in captured if turn['role']=='user']==['Water']
        params = {'conversation_id':a}
        assert c.delete('/api/chat/conversations/selected',headers=other,params=params).is_success
        assert len(c.get('/api/chat/history',headers=owner,params=params).json()['exchanges'])==2
        assert c.delete('/api/chat/conversations/selected',headers=owner,params=params).is_success
        assert send(owner,'Stale reply',a).status_code==404
        assert [r['title'] for r in c.get('/api/chat/conversations',headers=owner).json()]==['Power','Previous history']
        assert c.delete('/api/chat/conversations',headers=owner).is_success
        assert c.get('/api/chat/conversations',headers=owner).json()==[]
        assert c.get('/api/chat/conversations',headers=other).json()[0]['title']=='Independent history'


def test_admin_simulator_lifecycle():
    from sqlalchemy import select
    from app.database import SessionLocal
    from app.models import User
    with TestClient(app) as c:
        result = c.post('/api/auth/register',json={'name':'Simulator staff','email':'simadmin@example.org','password':'TestPassword42','is_admin':True})
        assert result.status_code in (200,201)
        headers = auth(c,'simadmin@example.org','TestPassword42')
        assert c.get('/api/admin/devices').status_code == 401
        assert c.post('/api/admin/simulators',headers=headers).status_code == 403
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email=='simadmin@example.org'))
            user.is_admin = True
            db.commit()
        created = c.post('/api/admin/simulators', headers=headers)
        assert created.status_code == 201 and created.headers['cache-control'] == 'no-store'
        keys = created.json()
        assert keys['qr'].startswith('data:image/png;base64,')
        pair = c.post('/api/trees', headers=headers,json={'name':'Test urban','location':'Test city','code':keys['code'],'claim_token':keys['claim']})
        assert pair.status_code == 201, pair.text
        assert c.post('/api/device/'+keys['code']+'/sensors',headers={'X-Device-Key':keys['telemetry']},json={'temperature_c':20}).status_code == 409
        listing = c.get('/api/admin/devices', headers=headers)
        assert any(row['code']==keys['code'] and row['status']=='active' for row in listing.json()['devices'])
        assert keys['claim'] not in listing.text and keys['telemetry'] not in listing.text


def test_password_recovery(monkeypatch):
    from datetime import timedelta
    from app import password_reset as recovery
    monkeypatch.setenv('PASSWORD_RESET_ORIGIN','https://example.org')
    monkeypatch.setenv('RESEND_API_KEY','test-only')
    monkeypatch.setenv('PASSWORD_RESET_FROM','mail@example.org')
    messages = []
    def send(url, **kwargs):
        messages.append(kwargs['json'])
        return type('Result', (), {'raise_for_status':lambda self: None})()
    monkeypatch.setattr(recovery.httpx,'post',send)
    email = 'recovery@example.org'
    with TestClient(app) as c:
        old = 'PasswordBefore123'
        new = 'PasswordAfter456'
        assert c.post('/api/auth/register',json={'email':email,'name':'Recovery test','password':old}).is_success
        session = auth(c,email,old)
        def request(address):
            return c.post('/api/auth/forgot-password',json={'email':address})
        missing = request('nobody123@example.org')
        issued = request(email)
        assert missing.status_code == issued.status_code == 202 and missing.json() == issued.json()
        assert len(messages) == 1 and messages[0]['to'] == [email]
        token = messages[0]['text'].split('https://example.org/#/reset-password/')[1]
        payload = {'token':token,'password':new}
        assert c.post('/api/auth/reset-password',json=payload).status_code == 200
        assert c.post('/api/auth/reset-password',json=payload).status_code == 400
        assert c.get('/api/auth/me',headers=session).status_code == 401
        assert c.post('/api/auth/login',json={'email':email,'password':old}).status_code == 401
        assert c.get('/api/auth/me',headers=auth(c,email,new)).status_code == 200
        request(email)
        later = recovery.utcnow() + timedelta(minutes=31)
        monkeypatch.setattr(recovery,'utcnow',lambda:later)
        payload['token'] = messages[-1]['text'].split('https://example.org/#/reset-password/')[1]
        assert c.post('/api/auth/reset-password',json=payload).status_code == 400

def test_three_profile_limit_and_owner_departure():
    from hashlib import sha256
    from app.database import SessionLocal
    from app.models import DeviceRegistration
    code='SHARED-TEST-3'
    token='test-claim-sharing-3'
    with TestClient(app) as c:
        with SessionLocal() as db:
            db.add(DeviceRegistration(code=code,model_code='ST-URBAN-2KW',kind='private',
                claim_hash=sha256(token.encode()).hexdigest(),telemetry_hash='test'))
            db.commit()
        profiles=[]
        for i in range(4):
            account=c.post('/api/auth/register',json={'name':f'Share {i}','email':f'share{i}@example.org','password':'TestPassword654'}).json()
            profiles.append({'Authorization':'Bearer '+account['access_token']})
        payload={'name':'Shared Urban','location':'Test location','code':code,'claim_token':token,'lat':None,'lng':None}
        def add(headers):
            return c.post('/api/trees',headers=headers,json=payload)
        first=add(profiles[0])
        assert first.status_code==201, first.text
        tree_id=first.json()['id']
        for profile in profiles[1:3]:
            assert add(profile).json()['id']==tree_id
        assert add(profiles[3]).json()['id']==tree_id
        url=f'/api/trees/{tree_id}'
        assert c.delete(url,headers=profiles[0]).status_code==200
        assert c.get(url,headers=profiles[0]).status_code==404
        assert c.get(url,headers=profiles[1]).status_code==200
        assert add(profiles[3]).status_code==409

def test_support_queue_privacy_and_agent_replies():
    from app.database import SessionLocal
    from app.models import SupportAgent, Tree
    with TestClient(app) as c:
        profiles=[]
        for i in range(3):
            account=c.post('/api/auth/register',json={'name':f'Support {i}','email':f'support{i}@example.org','password':'TestPassword654'}).json()
            profiles.append({'Authorization':'Bearer '+account['access_token']})
        owner,other,agent=profiles
        owner_id=c.get('/api/auth/me',headers=owner).json()['id']
        with SessionLocal() as db:
            db.add(Tree(code='SUPPORT-TEST',name='Support tree',kind='private',location='Test',owner_id=owner_id))
            db.add(SupportAgent(user_id=account['user']['id']))
            db.commit()
        tree=c.get("/api/trees",headers=owner).json()[0]
        case=c.post('/api/support',headers=owner,json={'subject':'WiFi problem','category':'connection','channel':'chat','body':'Connection interrupted.','tree_id':tree['id']}).json()
        path=f"/api/support/{case['id']}"
        assert c.get(path,headers=other).status_code==404
        assert c.post(path+'/reply',headers=other,json={'body':'Hello'}).status_code==404
        assert c.get('/api/support',headers=agent).json()['agent']
        assert c.post('/api/support/presence',headers=agent).status_code==200
        assert c.get('/api/support',headers=owner).json()['online']
        assert c.post(path+'/reply',headers=agent,json={'body':'Hello'}).status_code==409
        before=c.get(path,headers=agent).json()
        assert before['stats'] is None and before['serial'] is None
        assert c.post(path+'/accept',headers=agent).status_code==200
        from PIL import Image
        import io,base64
        avatar=io.BytesIO()
        Image.new('RGB',(32,36),'green').save(avatar,format='PNG')
        photo=c.put('/api/profile/photo',headers=owner,json={'image':base64.b64encode(avatar.getvalue()).decode()})
        assert photo.status_code==200
        assert c.get('/api/profile/photo',headers=other).json()['image'] is None
        assert c.put('/api/profile/photo',headers=owner,json={'image':'invalid'}).status_code==422
        active=c.get(path,headers=agent).json()
        assert active['customer_photo']==photo.json()['image']
        assert active['serial']==tree['code'] and 'power_w' in active['stats']
        assert c.get('/api/trees/'+str(tree['id']),headers=agent).status_code==404
        assert c.post(path+'/reply',headers=agent,json={'body':'How can I help?','file':{'name':'notes.txt','content':'dGVzdA=='}}).status_code==200
        thread=c.get(path,headers=owner).json()
        attachment=thread['messages'][-1]
        assert attachment['file']=='notes.txt'
        file_path=f"{path}/files/{attachment['id']}"
        assert c.get(file_path,headers=owner).content==b'test'
        assert c.get(file_path,headers=other).status_code==404
        assert len(thread['messages'])==2 and thread['agent']=='Support 2'
        batch=[{'name':'first.pdf','content':'YQ=='},{'name':'second.png','content':'Yg=='}]
        assert c.post(path+'/reply',headers=owner,json={'body':'Files','files':batch}).status_code==200
        before=c.get(path,headers=agent).json()['messages']
        assert [m['file'] for m in before[-2:]]==['first.pdf','second.png']
        batch[0]['content']=base64.b64encode(bytes(5*1024*1024)).decode()
        assert c.post(path+'/reply',headers=owner,json={'body':'Oversize','files':batch}).status_code==413
        assert len(c.get(path,headers=owner).json()['messages'])==len(before)
        assert c.post(path+'/close',headers=owner).status_code==200
        assert c.get(file_path,headers=agent).status_code==404
        assert c.post(path+'/reply',headers=agent,json={'body':'Hello'}).status_code==404

        assert c.put(path+'/rating',headers=other,json={'stars':5}).status_code==404
        assert c.put(path+'/rating',headers=owner,json={'stars':6}).status_code==422
        for stars in (4,5):
            assert c.put(path+'/rating',headers=owner,json={'stars':stars}).status_code==200
        assert c.get('/api/profile/support-rating',headers=agent).json()=={'average':5,'count':1}
        assert c.get(path,headers=agent).status_code==404
        assert not any(r['id']==case['id'] for r in c.get('/api/support',headers=agent).json()['tickets'])
        assert c.get(path,headers=owner).status_code==404
        assert not any(r['id']==case['id'] for r in c.get('/api/support',headers=owner).json()['tickets'])
        assert c.get('/api/support/archive',headers=owner).status_code==403
        archive=c.get('/api/support/archive',headers=agent).json()
        assert any(r['id']==case['id'] and set(r)=={'id','category','accepted'} for r in archive)
        assert c.get('/api/support/notices',headers=owner).json()[0]['id']==case['id']
        assert c.post(path+'/dismiss',headers=other).status_code==404
        assert c.post(path+'/dismiss',headers=owner).status_code==200
        assert c.get('/api/support/notices',headers=owner).json()==[]

        payload={'category':'other','subject':'Testing','body':'Test message','channel':'ticket'}
        inquiry=c.post('/api/support',headers=owner,json=payload).json()['id']
        assert c.delete(f'/api/support/{inquiry}',headers=other).status_code==404
        assert c.delete(f'/api/support/{inquiry}',headers=owner).status_code==200
        assert c.get(f'/api/support/{inquiry}',headers=agent).status_code==404

        from app.models import LiveLease
        from datetime import datetime,timedelta,timezone
        idle=c.post('/api/support',headers=owner,json={**payload,'channel':'chat'}).json()['id']
        path=f'/api/support/{idle}'
        assert c.post(path+'/accept',headers=agent).status_code==200
        assert c.post(path+'/typing',headers=owner).status_code==200
        assert c.get(path,headers=agent).json()['typing']
        with SessionLocal() as db:
            lease=db.get(LiveLease,idle)
            lease.customer_seen=lease.agent_seen=datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(seconds=301)
            db.commit()
        assert c.get(path,headers=agent).status_code==404
        assert c.post(path+'/typing',headers=owner).status_code==404




def test_existing_printed_qr_codes_can_be_reused_by_additional_accounts():
    """Printed Prototype P1 and old Urban labels remain valid with shared history."""
    from app.database import SessionLocal
    from app.models import TreeMember
    with TestClient(app) as c:
        account = c.post('/api/auth/register', json={
            'name': 'QR Viewer', 'email': 'qrviewer2026@example.org',
            'password': 'StrongTestPassword2026'})
        assert account.status_code == 201, account.text
        viewer = {'Authorization': 'Bearer ' + account.json()['access_token']}
        cases = [
            ('IVAN-TREE-0001', 'IVAN-TREE-0001', 'IVAN-PROTOTYPE-PAIR-2026'),
            ('URBAN-TREE-0001', 'SOLIX-ARC-0001', 'URBAN-2KW-PAIR-2026'),
        ]
        for printed_serial, canonical, printed_token in cases:
            lookup = c.post('/api/pair/resolve', headers=viewer, json={
                'code': printed_serial, 'claim_token': printed_token})
            assert lookup.status_code == 200, lookup.text
            assert lookup.json()['code'] == canonical
            existing = None
            with SessionLocal() as db:
                from app.models import Tree
                from sqlalchemy import select
                existing = db.scalar(select(Tree).where(Tree.code == canonical))
                assert existing is not None
                original_owner = existing.owner_id
                tree_id = existing.id
            joined = c.post('/api/trees', headers=viewer, json={
                'name': 'My shared view', 'code': printed_serial,
                'claim_token': printed_token, 'location': 'Viewing only',
                'lat': None, 'lng': None})
            assert joined.status_code == 201, joined.text
            assert joined.json()['id'] == tree_id
            assert c.get(f'/api/trees/{tree_id}', headers=viewer).status_code == 200
            assert c.get(f'/api/trees/{tree_id}/readings', headers=viewer).status_code == 200
            assert c.patch(f'/api/trees/{tree_id}/coordinates', headers=viewer,
                json={'lat': 42.0, 'lng': 25.0}).status_code == 403
            assert c.put(f'/api/trees/{tree_id}/maintenance/water_filter',
                headers=viewer, json={'interval_days': 90}).status_code == 403
            assert c.post('/api/pair/resolve', headers=viewer, json={
                'code': printed_serial, 'claim_token': printed_token}).status_code == 409
            with SessionLocal() as db:
                from app.models import Tree
                assert db.get(Tree, tree_id).owner_id == original_owner
                assert db.get(TreeMember, (tree_id, account.json()['user']['id'])) is not None
        listing = c.get('/api/trees', headers=viewer)
        assert listing.status_code == 200
        assert {t['code'] for t in listing.json()} >= {'IVAN-TREE-0001', 'SOLIX-ARC-0001'}
