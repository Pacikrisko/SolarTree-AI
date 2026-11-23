"""CLI-only creation of a municipality account. No public role escalation endpoint."""
import argparse
from getpass import getpass
from sqlalchemy import select
from app.database import Base, engine, SessionLocal
from app.models import User
from app.security import hash_password

def main():
    parser=argparse.ArgumentParser(description='Create a municipality staff account locally.')
    parser.add_argument('--email',required=True)
    parser.add_argument('--name',required=True)
    args=parser.parse_args()
    password=getpass('Парола (поне 12 символа): ')
    if len(password)<12:raise SystemExit('Паролата трябва да е минимум 12 символа.')
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        email=args.email.strip().lower()
        if db.scalar(select(User).where(User.email==email)):
            raise SystemExit('Профил с този адрес вече съществува.')
        db.add(User(name=args.name.strip(),email=email,password_hash=hash_password(password),role='municipality'))
        db.commit()
    print('Общинският профил е създаден.')
if __name__=='__main__':main()
