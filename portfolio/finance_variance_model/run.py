"""Generate fictional financial facts, execute SQL, independently reconcile."""
import json
import random
import sqlite3
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def build():
    rng = random.Random(20261019)
    months = [(m, f'2025-{m:02}-01') for m in range(1, 13)]
    units = [(1, 'Consumer'), (2, 'Enterprise'), (3, 'Partner')]
    plan, actual = [], []
    for m, _ in months:
        for u, _ in units:
            qty, price, cost = 12000 + 800*u + 200*m, 9000+1500*u, 5200+700*u
            plan.append((m,u,qty,price,cost))
            # Predetermined fictional scenario: Enterprise growth; Consumer cost pressure.
            for j in range(100):
                q = max(1,qty//100 + rng.randint(-25,25) + (15 if u==2 else -3))
                p = price + rng.randint(-300,300) + (250 if u==3 else -100)
                c = cost + rng.randint(-200,200) + (450 if u==1 else 80)
                actual.append((len(actual)+1,m,u,q,p,c))
    db = sqlite3.connect(':memory:')
    db.executescript((ROOT/'schema.sql').read_text())
    db.executemany('INSERT INTO dim_month VALUES (?,?)',months)
    db.executemany('INSERT INTO dim_unit VALUES (?,?)',units)
    db.executemany('INSERT INTO fact_plan VALUES (?,?,?,?,?)',plan)
    db.executemany('INSERT INTO fact_actual VALUES (?,?,?,?,?,?)',actual)
    db.row_factory=sqlite3.Row
    bridge=[dict(r) for r in db.execute('SELECT * FROM variance_bridge ORDER BY month_id,unit_id')]
    checks={}
    checks['foreign_keys']=not list(db.execute('PRAGMA foreign_key_check'))
    checks['complete_plan_grid']=len(plan)==36
    checks['actual_grain']=len(actual)==len({r[0] for r in actual})==3600
    checks['bridge_grain']=len(bridge)==36
    checks['all_cells_reconciled']=True
    for row in bridge:
        m,u=row['month_id'],row['unit_id']
        records=[r for r in actual if r[1:3]==(m,u)]
        p=next(p for p in plan if p[:2]==(m,u))
        aq=sum(r[3] for r in records)
        ar=sum(r[3]*r[4] for r in records)
        ac=sum(r[3]*r[5] for r in records)
        independent=[p[2],aq,p[2]*p[3],ar,p[2]*(p[3]-p[4]),ar-ac,
                     (aq-p[2])*(p[3]-p[4]),ar-aq*p[3],aq*p[4]-ac]
        checks['all_cells_reconciled'] &= list(row.values())[2:]==independent
    checks['exact_bridge_identity']=all(r['actual_margin_cents']-r['budget_margin_cents']==
        r['volume_effect_cents']+r['price_effect_cents']+r['cost_effect_cents'] for r in bridge)
    checks['raw_revenue_reconciled']=sum(r['actual_revenue_cents'] for r in bridge)==sum(r[3]*r[4] for r in actual)
    checks['raw_margin_reconciled']=sum(r['actual_margin_cents'] for r in bridge)==sum(r[3]*(r[4]-r[5]) for r in actual)
    # Demonstrate why joining transaction-grain actuals to monthly budgets is wrong.
    inflated=db.execute('SELECT SUM(p.units*p.price_cents) FROM fact_actual a JOIN fact_plan p USING(month_id,unit_id)').fetchone()[0]
    correct=sum(p[2]*p[3] for p in plan)
    checks['fanout_regression']=inflated==100*correct
    try:
        db.execute('INSERT INTO fact_plan VALUES (1,1,1,1,1)')
        checks['duplicate_rejected']=False
    except sqlite3.IntegrityError: checks['duplicate_rejected']=True
    try:
        db.execute('INSERT INTO fact_actual VALUES (99999,99,1,1,1,1)')
        checks['orphan_rejected']=False
    except sqlite3.IntegrityError: checks['orphan_rejected']=True
    assert all(checks.values()), checks
    totals={k:sum(r[k] for r in bridge) for k in bridge[0] if k not in ('month_id','unit_id')}
    by_unit={name:{k:sum(r[k] for r in bridge if r['unit_id']==u) for k in totals} for u,name in units}
    out=ROOT/'outputs';out.mkdir(exist_ok=True)
    model=ROOT/'generated';model.mkdir(exist_ok=True)
    for table in ['dim_month','dim_unit','fact_plan','fact_actual']:
        (model/f'{table}.json').write_text(json.dumps([dict(r) for r in db.execute(f'SELECT * FROM {table}')],indent=2)+'\n')
    for name,value in [('bridge',bridge),('summary',{'totals':totals,'by_unit':by_unit}),('validation',{
        'status':'PASS','checks':checks,'sqlite_version':sqlite3.sqlite_version,
        'seed':20261019,'source_sha256':hashlib.sha256(json.dumps([plan,actual]).encode()).hexdigest(),
        'power_bi_execution':'Not executed; import recipe and DAX supplied for manual validation.'})]:
        (out/f'{name}.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({'totals':totals,'checks_passed':len(checks),'by_unit':by_unit},indent=2))

if __name__=='__main__': build()
