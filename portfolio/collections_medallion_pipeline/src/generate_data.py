"""Generate deterministic fictional account, payment, and contact-event batches."""
from __future__ import annotations
import csv, json, random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261012
ACCOUNT_COUNT = 50_000
EVENT_COUNT = 300_000
START = date(2025, 1, 1)
REGIONS = ['Northeast', 'South', 'Midwest', 'West']
PRODUCTS = ['Credit Card', 'Personal Loan', 'Auto Loan']
CHANNELS = ['phone', 'sms', 'email', 'letter']

def _write_jsonl(path, rows):
    with path.open('w', encoding='utf-8') as f:
        for row in rows: f.write(json.dumps(row, separators=(',', ':'))+'\n')

def _write_shards(directory, rows, shard_size=100_000):
    for old in directory.glob('events*.jsonl'):
        old.unlink()
    for index, start in enumerate(range(0, len(rows), shard_size), 1):
        _write_jsonl(directory/f'events_{index:03}.jsonl', rows[start:start+shard_size])

def generate(root=ROOT):
    root=Path(root); rng=random.Random(SEED)
    for batch in ['batch_01','batch_02']:(root/'data/raw'/batch).mkdir(parents=True,exist_ok=True)
    accounts=[]
    for account_id in range(1,ACCOUNT_COUNT+1):
        opened=START-timedelta(days=rng.randint(30,900))
        balance=rng.randint(20_000,2_000_000)
        accounts.append({'account_id':account_id,'opened_date':opened.isoformat(),
                         'region':rng.choice(REGIONS),'product':rng.choice(PRODUCTS),
                         'starting_balance_cents':balance,'assigned_team':f'Team {rng.randint(1,8):02}'})
    with (root/'data/raw/accounts.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(accounts[0]));w.writeheader();w.writerows(accounts)
    events=[];event_id=0
    account_state={a['account_id']:{'balance':a['starting_balance_cents'],'last':START} for a in accounts}
    for _ in range(EVENT_COUNT):
        event_id+=1;aid=rng.randint(1,ACCOUNT_COUNT);state=account_state[aid]
        dt=START+timedelta(days=rng.randint(0,364));etype=rng.choices(['contact','payment'],[.72,.28])[0]
        if state['balance']<=0: etype='contact'
        if etype=='payment':
            amount=min(state['balance'],rng.randint(1_000,60_000));state['balance']-=amount
            row={'event_id':f'E{event_id:09}','account_id':aid,'event_ts':dt.isoformat()+'T12:00:00Z',
                 'event_type':'payment','channel':None,'contact_result':None,'amount_cents':amount,
                 'source_system':rng.choice(['PAYMENTS_A','PAYMENTS_B'])}
        else:
            channel=rng.choice(CHANNELS)
            result=rng.choices(['right_party_contact','no_answer','promise_to_pay','dispute','wrong_party'],[.19,.42,.14,.08,.17])[0]
            row={'event_id':f'E{event_id:09}','account_id':aid,'event_ts':dt.isoformat()+'T12:00:00Z',
                 'event_type':'contact','channel':channel,'contact_result':result,'amount_cents':0,
                 'source_system':'COLLECTIONS_CRM'}
        events.append(row)
    events.sort(key=lambda x:(x['event_ts'],x['event_id']))
    split=int(len(events)*.68)
    batch1=events[:split];batch2=events[split:]
    # Add exact duplicate deliveries and invalid records for quarantine testing.
    batch2.extend(dict(x) for x in batch1[::750])
    invalid=[
        {'event_id':'BAD000001','account_id':999999,'event_ts':'2025-08-10T12:00:00Z','event_type':'payment','channel':None,'contact_result':None,'amount_cents':5000,'source_system':'PAYMENTS_A'},
        {'event_id':'BAD000002','account_id':12,'event_ts':'not-a-date','event_type':'contact','channel':'phone','contact_result':'no_answer','amount_cents':0,'source_system':'COLLECTIONS_CRM'},
        {'event_id':'BAD000003','account_id':13,'event_ts':'2025-09-01T12:00:00Z','event_type':'payment','channel':None,'contact_result':None,'amount_cents':-500,'source_system':'PAYMENTS_B'},
    ]
    batch2.extend(invalid)
    _write_shards(root/'data/raw/batch_01',batch1)
    _write_shards(root/'data/raw/batch_02',batch2)
    metadata={'seed':SEED,'accounts':len(accounts),'canonical_events':len(events),'batch_01_rows':len(batch1),
              'batch_02_rows':len(batch2),'intentional_duplicate_rows':len(batch1[::750]),
              'intentional_invalid_rows':len(invalid),'period':['2025-01-01','2025-12-31'],'fully_synthetic':True}
    (root/'data/generation_metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return metadata

if __name__=='__main__':print(json.dumps(generate(),indent=2))
