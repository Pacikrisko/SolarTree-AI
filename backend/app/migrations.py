"""Minimal additive SQLite migration for v0.2 users. Other DBs use Alembic in production."""
from sqlalchemy import text

def upgrade(engine):
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
