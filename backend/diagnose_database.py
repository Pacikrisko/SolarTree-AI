"""Non-destructive, local SQLite checks for registration failures.

Run from backend: .venv\\Scripts\\python.exe diagnose_database.py
Prints no user email, password, token or API key.
"""
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.engine import make_url
from app.database import DATABASE_URL, engine


def main():
    print('\nSolarTree AI - diagnostics for account registration')
    url = make_url(DATABASE_URL)
    if url.get_backend_name() != 'sqlite':
        print('Database type:', url.get_backend_name())
        print('This script currently checks SQLite databases only.')
        return
    filename = url.database
    if filename is None or filename == ':memory:':
        print('Database is stored in memory. Restarting clears users.')
        return
    path = Path(filename).resolve()
    print('Database file:', path)
    print('Database file exists:', path.exists())
    print('Database folder exists:', path.parent.is_dir())
    try:
        with engine.connect() as connection:
            present = connection.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").first()
            print('Users table exists:', bool(present))
            if present:
                names = {row[1] for row in connection.exec_driver_sql('PRAGMA table_info(users)')}
                expected = {'id', 'name', 'email', 'password_hash', 'role', 'created_at'}
                print('Required user columns present:', expected.issubset(names))
                print('Missing columns:', ', '.join(sorted(expected - names)) if expected - names else 'none')
            print('Database integrity:', connection.exec_driver_sql('PRAGMA integrity_check').scalar())
            connection.rollback()
        with engine.connect() as connection:
            connection.exec_driver_sql('BEGIN IMMEDIATE')
            connection.exec_driver_sql('ROLLBACK')
            print('Database permits writing: yes')
    except Exception as exc:
        print('Diagnostic failure type:', type(exc).__name__)
        print('Diagnostic failure:', str(exc))
    print('If the registration still fails, copy ONLY the traceback from the backend terminal; never share passwords or API keys.\n')


if __name__ == '__main__':
    main()
