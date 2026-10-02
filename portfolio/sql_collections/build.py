"""Generate, validate and export a deterministic SQLite portfolio. Standard library only."""
import csv, json, random, sqlite3
from datetime import date, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parent
rng = random.Random(42)
SNAPSHOT = date(2026, 6, 30)

def build():
    # In memory: no existing database is overwritten.
    db = sqlite3.connect(':memory:')
    db.executescript((ROOT/'schema.sql').read_text())
    db.executemany('INSERT INTO collectors VALUES (?,?)', enumerate(['Alex','Casey','Jordan','Morgan','Riley','Taylor','Unassigned'],1))
    db.executemany('INSERT INTO customers VALUES (?,?,?)', [(i,rng.choice(['Northeast','South','Midwest','West']),rng.randint(420,820)) for i in range(1,1201)])
    pid = cid = 0
    for i in range(1,1501):
        placed = date(2026,1,1)+timedelta(days=rng.randrange(150))
        balance = rng.randrange(50000,2500001)
        collector = rng.randrange(1,7)
        customer = i if i <= 1200 else rng.randrange(1,1201)
        db.execute('INSERT INTO accounts VALUES (?,?,?,?,?,?,?)',(i,customer,collector,rng.choice(['Credit Card','Medical','Personal Loan','Auto']),placed.isoformat(),balance,rng.randrange(0,241)))
        remaining = balance
        for _ in range(rng.randrange(0,5)):
            amount = min(remaining,rng.randrange(1000,max(1001,balance//8)))
            if amount <= 0: break
            pid += 1
            paid = placed+timedelta(days=rng.randrange((SNAPSHOT-placed).days+1))
            db.execute('INSERT INTO payments VALUES (?,?,?,?)',(pid,i,paid.isoformat(),amount))
            remaining -= amount
        promised = False
        for _ in range(rng.randrange(0,9)):
            contact = placed+timedelta(days=rng.randrange((SNAPSHOT-placed).days+1))
            outcome = rng.choices(['No answer','Wrong number','RPC','PTP'],[50,10,30,10])[0]
            if outcome == 'PTP' and promised: outcome = 'RPC'
            due = amount = None
            if outcome == 'PTP':
                promised=True
                due=(contact+timedelta(days=14)).isoformat()
                amount=min(balance,10000)
            cid += 1
            db.execute('INSERT INTO contact_attempts VALUES (?,?,?,?,?,?,?)',(cid,i,collector,contact.isoformat(),outcome,due,amount))
    db.commit()
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    assert db.execute('SELECT COUNT(*) FROM account_summary').fetchone()[0]==1500
    assert db.execute('SELECT SUM(collected_cents) FROM account_summary').fetchone()[0]==db.execute('SELECT SUM(amount_cents) FROM payments').fetchone()[0]
    assert db.execute('SELECT MIN(outstanding_cents) FROM account_summary').fetchone()[0]>=0
    assert db.execute('SELECT COUNT(*) FROM payments p JOIN accounts a USING(account_id) WHERE p.payment_date<a.placed_date OR p.payment_date>"2026-06-30"').fetchone()[0]==0
    # Fixtures specifically detect fact fanout and retain accounts with no events.
    db.execute('SAVEPOINT fixtures')
    db.execute("INSERT INTO accounts VALUES (9999,1,7,'Auto','2026-01-01',100000,90)")
    db.execute("INSERT INTO accounts VALUES (9998,1,7,'Auto','2026-01-01',100000,0)")
    db.executemany('INSERT INTO payments VALUES (?,?,?,?)',[(99998,9999,'2026-02-01',10000),(99999,9999,'2026-02-02',20000)])
    db.executemany('INSERT INTO contact_attempts VALUES (?,?,?,?,?,?,?)',[(99990+n,9999,7,'2026-01-10','RPC',None,None) for n in range(3)])
    assert db.execute('SELECT collected_cents,attempts,outstanding_cents FROM account_summary WHERE account_id=9999').fetchone()==(30000,3,70000)
    assert db.execute('SELECT collected_cents,attempts FROM account_summary WHERE account_id=9998').fetchone()==(0,0)
    db.execute('ROLLBACK TO fixtures')
    db.execute('RELEASE fixtures')
    out=ROOT/'outputs'; out.mkdir(exist_ok=True)
    sql='\n'.join(line for line in (ROOT/'analysis.sql').read_text().splitlines() if not line.lstrip().startswith('--'))
    queries=[q.strip() for q in sql.split(';') if q.strip()]
    assert len(queries)==20
    counts={}
    for n,query in enumerate(queries,1):
        cur=db.execute(query); rows=cur.fetchall()
        counts[f'Q{n:02}']=len(rows)
        with (out/f'q{n:02}.csv').open('w',newline='') as f:
            writer=csv.writer(f); writer.writerow([d[0] for d in cur.description]); writer.writerows(rows)
    data=ROOT/'data'; data.mkdir(exist_ok=True)
    tables=['collectors','customers','accounts','payments','contact_attempts']
    for table in tables:
        cur=db.execute(f'SELECT * FROM {table}')
        with (data/f'{table}.csv').open('w',newline='') as f:
            w=csv.writer(f);w.writerow([d[0] for d in cur.description]);w.writerows(cur.fetchall())
    (data/'seed.sql').write_text('\n'.join(db.iterdump())+'\n')
    report={'seed':42,'snapshot':SNAPSHOT.isoformat(),'tables':{t:db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in tables},'queries_executed':20,'query_row_counts':counts,'checks':['integrity','foreign keys','account grain','payment reconciliation','nonnegative balance','payment dates','fanout fixture','zero activity fixture']}
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    db.backup(sqlite3.connect(ROOT/'collections.db'))
    print(json.dumps(report,indent=2))
if __name__=='__main__': build()
