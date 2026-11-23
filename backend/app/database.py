import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./solartree.db').strip()
# Neon and many hosting panels return a plain postgresql:// URL. SQLAlchemy needs
# an explicit driver when using psycopg v3; local SQLite remains fully supported.
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = 'postgresql+psycopg://' + DATABASE_URL[len('postgres://'):]
elif DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = 'postgresql+psycopg://' + DATABASE_URL[len('postgresql://'):]

engine = create_engine(
    DATABASE_URL,
    connect_args={'check_same_thread': False, 'timeout': 15.0} if DATABASE_URL.startswith('sqlite') else {},
    pool_pre_ping=True,
    pool_recycle=1800,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    with SessionLocal() as session:
        yield session
