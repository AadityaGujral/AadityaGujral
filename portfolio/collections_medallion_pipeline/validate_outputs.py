"""Independent standard-library reconciliation of Spark outputs against raw JSONL."""
from __future__ import annotations
import csv, hashlib, json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def validate(root=ROOT):
    root=Path(root);meta=json.loads((root/'data/generation_metadata.json').read_text())
    accounts={}
    with (root/'data/raw/accounts.csv').open() as f:
        for r in csv.DictReader(f):accounts[int(r['account_id'])]=r
    delivered=[]
    for batch in ['batch_01','batch_02']:
        for path in sorted((root/'data/raw'/batch).glob('events_*.jsonl')):
            with path.open() as f:
                delivered.extend((batch,json.loads(line)) for line in f)
    valid={};reasons=defaultdict(int)
    for batch,r in delivered:
        try:dt=datetime.fromisoformat(r['event_ts'].replace('Z','+00:00'))
        except (ValueError,AttributeError):reasons['invalid_timestamp']+=1;continue
        if r.get('account_id') not in accounts:reasons['unknown_account']+=1;continue
        if r.get('event_type') not in {'payment','contact'}:reasons['invalid_event_type']+=1;continue
        if r.get('amount_cents') is None or r['amount_cents']<0:reasons['invalid_amount']+=1;continue
        if r['event_type']=='payment' and r['amount_cents']<=0:reasons['nonpositive_payment']+=1;continue
        if r['event_type']=='contact' and not r.get('channel'):reasons['missing_contact_channel']+=1;continue
        # Later batch wins by deterministic lexical batch order.
        valid[r['event_id']]=(batch,r,dt)
    by_channel=defaultdict(lambda:defaultdict(int));monthly=defaultdict(lambda:defaultdict(int));by_account=defaultdict(int)
    payment_events=contact_events=payments=0
    for _,r,dt in valid.values():
        a=accounts[r['account_id']];key=(dt.strftime('%Y-%m'),a['region'],a['product'])
        monthly[key]['active_accounts_set'].add(r['account_id']) if 'active_accounts_set' in monthly[key] else monthly[key].update(active_accounts_set={r['account_id']})
        if r['event_type']=='payment':
            payment_events+=1;payments+=r['amount_cents'];by_account[r['account_id']]+=r['amount_cents'];monthly[key]['payment_events']+=1;monthly[key]['payments_cents']+=r['amount_cents']
        else:
            contact_events+=1;monthly[key]['contact_attempts']+=1;by_channel[r['channel']]['attempts']+=1
            if r['contact_result'] in {'right_party_contact','promise_to_pay'}:
                monthly[key]['right_party_contacts']+=1;by_channel[r['channel']]['right_party_contacts']+=1
            if r['contact_result']=='promise_to_pay':
                monthly[key]['promises_to_pay']+=1;by_channel[r['channel']]['promises_to_pay']+=1
    spark_summary=json.loads((root/'outputs/portfolio_summary.json').read_text())
    active=set(by_account)|{r['account_id'] for _,r,_ in valid.values() if r['event_type']=='contact'}
    start=sum(int(accounts[a]['starting_balance_cents']) for a in active)
    remaining=sum(max(0,int(accounts[a]['starting_balance_cents'])-by_account[a]) for a in active)
    checks={
      'canonical_event_count':len(valid)==meta['canonical_events']==spark_summary['events'],
      'intentional_invalid_count':sum(reasons.values())==meta['intentional_invalid_rows']==3,
      'duplicate_delivery_removed':len(delivered)-sum(reasons.values())-len(valid)==meta['intentional_duplicate_rows'],
      'payment_event_count':payment_events==spark_summary['payment_events'],
      'contact_event_count':contact_events==spark_summary['contact_events'],
      'payment_cents_reconciled':payments==spark_summary['payments_cents'],
      'active_accounts_reconciled':len(active)==spark_summary['accounts'],
      'starting_balance_reconciled':start==spark_summary['starting_balance_cents'],
      'remaining_balance_reconciled':remaining==spark_summary['remaining_balance_cents'],
    }
    with (root/'outputs/channel_performance.csv').open() as f:
        rows={r['channel']:r for r in csv.DictReader(f)}
    checks['channel_mart_reconciled']=all(int(rows[c][m])==v for c,metrics in by_channel.items() for m,v in metrics.items())
    with (root/'outputs/monthly_kpis.csv').open() as f:
        rows={(r['event_month'],r['region'],r['product']):r for r in csv.DictReader(f)}
    checks['monthly_mart_reconciled']=all(
        int(rows[k][m if m!='active_accounts_set' else 'active_accounts'])==(len(v) if isinstance(v,set) else v)
        for k,metrics in monthly.items() for m,v in metrics.items())
    batch=json.loads((root/'outputs/batch_metrics.json').read_text())
    checks['silver_key_uniqueness']=batch[-1]['silver_rows_after_merge']==batch[-1]['distinct_event_ids_after_merge']==len(valid)
    if not all(checks.values()):raise AssertionError({k:v for k,v in checks.items() if not v})
    report={'status':'PASS','checks':checks,'passed_checks':len(checks),'method':'Python standard library from raw CSV/JSONL; independent of Spark aggregations',
            'raw_deliveries':len(delivered),'canonical_events':len(valid),'quarantine_reasons':dict(sorted(reasons.items())),
            'input_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [root/'data/raw/accounts.csv',*sorted((root/'data/raw').glob('batch_*/events_*.jsonl'))]}}
    (root/'outputs/validation.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':print(json.dumps(validate(),indent=2))
