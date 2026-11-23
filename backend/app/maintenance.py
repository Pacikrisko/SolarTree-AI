"""Calendar-based maintenance suggestions; not measured filter/dryer condition."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Tree, Maintenance

COMPONENTS = {'water_filter': ('Филтър за пречистване на водата', 90),
              'oxygen_dryer': ('Модул за изсушаване на кислорода', 120)}

def initialize_maintenance(db: Session):
    trees = db.scalars(select(Tree)).all()
    for tree in trees:
        for component, (_, days) in COMPONENTS.items():
            exists = db.scalar(select(Maintenance).where(Maintenance.tree_id == tree.id, Maintenance.component == component))
            if exists:
                continue
            # existing sample trees: show a mix of upcoming and due maintenance
            age = ((103 if component == 'water_filter' else 91) if tree.code == 'STZ-002' else (84 if component == 'water_filter' else 40)) if tree.code in {'STZ-001', 'STZ-002', 'STZ-003', 'HOME-001'} else 0
            when = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=age)
            db.add(Maintenance(tree_id=tree.id, component=component, last_serviced_at=when, interval_days=days))
    db.commit()

def maintenance_for(db: Session, tree: Tree):
    entries = db.scalars(select(Maintenance).where(Maintenance.tree_id == tree.id)).all()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    out = []
    for e in entries:
        due = e.last_serviced_at + timedelta(days=e.interval_days)
        days = (due - now).days + (1 if (due - now).seconds > 0 else 0)
        out.append({'id':e.id, 'tree_id':tree.id,'tree_name':tree.name,
                    'component':e.component, 'label':COMPONENTS[e.component][0],
                    'last_service':e.last_serviced_at.isoformat()+'Z', 'due_at':due.isoformat()+'Z',
                    'days_left':days, 'status':'overdue' if days < 0 else 'soon' if days <= 14 else 'ok',
                    'basis':'calendar', 'interval_days':e.interval_days})
    return out
