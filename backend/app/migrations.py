"""Minimal additive SQLite migration for v0.2 users. Other DBs use Alembic in production."""
from sqlalchemy import inspect, text
from .catalog import get_model

def upgrade(engine):
    with engine.begin() as conn:
        inspector = inspect(conn)
        if inspector.has_table('tree_members'):
            columns = {column['name'] for column in inspector.get_columns('tree_members')}
            for name in ('pin_lat', 'pin_lng'):
                if name not in columns:
                    conn.execute(text(f'ALTER TABLE tree_members ADD COLUMN {name} FLOAT'))
        for table, column in [('trees','code'),('device_registrations','code'),('support_tickets','serial'),('device_warranties','serial')]:
            if inspector.has_table(table) and column in {c['name'] for c in inspector.get_columns(table)}:
                for old,new in [('URBAN-TREE-0001','SOLIX-ARC-0001'),('URBAN-TREE-0002','SOLIX-HALO-0002')]:
                    conn.execute(text(f'UPDATE {table} SET {column}=:new WHERE {column}=:old'),{'old':old,'new':new})
        if inspector.has_table('trees') and {'code', 'location', 'lat', 'lng'}.issubset(
            column['name'] for column in inspector.get_columns('trees')
        ):
            conn.execute(text("""UPDATE trees SET location='Stara Zagora', lat=42.4258, lng=25.6345
                WHERE code='IVAN-TREE-0001' AND lat IS NULL AND lng IS NULL"""))
        if inspector.has_table('trees') and {'code', 'name'}.issubset(
            column['name'] for column in inspector.get_columns('trees')
        ):
            for serial in ('SOLIX-ARC-0001', 'SOLIX-HALO-0002'):
                name = get_model('ST-URBAN-2KW', serial)['name']
                conn.execute(text("""
                    UPDATE trees SET name=:name
                    WHERE code=:serial AND (
                        lower(name) LIKE '%urban%' OR lower(name)='centere'
                    )
                """), {'name': name, 'serial': serial})
        if inspector.has_table('support_tickets'):
            conn.execute(text("""
                UPDATE support_tickets SET model=CASE
                    WHEN model='SolarTree Urban 5K' OR serial='SOLIX-HALO-0002' THEN 'Solix Halo 5K'
                    WHEN model='SolarTree Prototype P1' THEN 'Solix Prototype P1'
                    WHEN model='SolarTree Compact M6' THEN 'Solix Compact M6'
                    WHEN model='SolarTree Urban M8' THEN 'Solix Municipal M8'
                    ELSE 'Solix Arc 2K' END
                WHERE model IN ('SolarTree Urban 2K', 'SolarTree Urban 5K',
                    'SolarTree Prototype P1', 'SolarTree Compact M6', 'SolarTree Urban M8')
            """))
        if inspector.has_table('device_samples') and 'hydrogen_flow_lph' not in {c['name'] for c in inspector.get_columns('device_samples')}:
            conn.execute(text('ALTER TABLE device_samples ADD COLUMN hydrogen_flow_lph FLOAT'))
        if inspector.has_table("users") and "session_version" not in {c["name"] for c in inspector.get_columns("users")}:
            conn.execute(text("ALTER TABLE users ADD COLUMN session_version INTEGER NOT NULL DEFAULT 0"))
        if inspector.has_table("users") and "is_admin" not in {c["name"] for c in inspector.get_columns("users")}:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE"))
        if inspector.has_table('chat_exchanges') and 'conversation_id' not in {c['name'] for c in inspector.get_columns('chat_exchanges')}:
            conn.execute(text('ALTER TABLE chat_exchanges ADD COLUMN conversation_id VARCHAR(36)'))
        if inspector.has_table('device_registrations'):
            if 'bound_user_id' not in {c['name'] for c in inspector.get_columns('device_registrations')}:
                conn.execute(text('ALTER TABLE device_registrations ADD COLUMN bound_user_id INTEGER REFERENCES users(id)'))
            # Completed phone pairings identify the original municipal owner.
            conn.execute(text("""UPDATE trees SET owner_id = (
                SELECT min(user_id) FROM mobile_pair_sessions WHERE tree_id=trees.id AND status='completed'
                HAVING count(DISTINCT user_id)=1)
                WHERE kind='municipal' AND owner_id IS NULL"""))
            conn.execute(text("""UPDATE device_registrations SET bound_user_id = (
                SELECT owner_id FROM trees WHERE trees.id=device_registrations.claimed_tree_id)
                WHERE bound_user_id IS NULL AND claimed_tree_id IS NOT NULL"""))
    if engine.dialect.name != 'sqlite':
        return
    with engine.begin() as conn:
        for table, columns in {
            'trees': {
                'model_code': "VARCHAR(40) NOT NULL DEFAULT 'ST-M6'",
                'media_file': 'VARCHAR(100)',
                'media_mime': 'VARCHAR(40)',
            },
            'readings': {
                'electrolyzer_power_w': 'FLOAT',
                'oxygen_flow_lph': 'FLOAT',
                'oxygen_basis': "VARCHAR(16) NOT NULL DEFAULT 'unavailable'",
            },
        }.items():
            found={r[1] for r in conn.exec_driver_sql(f'PRAGMA table_info({table})').fetchall()}
            for name, definition in columns.items():
                if name not in found:
                    conn.exec_driver_sql(f'ALTER TABLE {table} ADD COLUMN {name} {definition}')
        conn.execute(text("UPDATE trees SET model_code='ST-M8' WHERE kind='municipal' AND model_code='ST-M6'"))
        # Historic synthetic data remains explicitly synthetic. Never fabricate device oxygen readings.
        conn.execute(text("UPDATE readings SET oxygen_flow_lph=ROUND(power_w*0.065,1), "
                          "electrolyzer_power_w=ROUND(power_w*0.65,1), oxygen_basis='simulation' "
                          "WHERE source='simulation' AND oxygen_flow_lph IS NULL"))
