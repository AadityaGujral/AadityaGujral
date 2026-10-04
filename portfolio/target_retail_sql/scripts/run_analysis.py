"""Execute actual SQL, export each answer, and independently reconcile revenue.

DuckDB is the portable execution path; SQL files target PostgreSQL.
No SQL rewriting or alternate analytical implementation is used.
"""
import csv, json, re
from decimal import Decimal
from pathlib import Path
import duckdb

ROOT=Path(__file__).resolve().parents[1]

def run():
    db=duckdb.connect()
    db.execute((ROOT/'sql/01_schema.sql').read_text())
    counts={}
    for table in ['categories','stores','customers','products','orders','order_items']:
        path=ROOT/'data'/f'{table}.csv'
        db.execute(f"COPY {table} FROM '{path}' (HEADER, DELIMITER ',')")
        counts[table]=db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    db.execute((ROOT/'sql/03_views.sql').read_text())
    results={}
    for path in sorted((ROOT/'sql').glob('*.sql')):
        if path.name[:2] not in ['04','05','06','07','08','09']: continue
        for block in re.split(r'-- query: ',path.read_text())[1:]:
            key,sql=block.split('\n',1)
            cur=db.execute(sql); names=[d[0] for d in cur.description]; rows=cur.fetchall()
            results[key]=[dict(zip(names,row)) for row in rows]
            with (ROOT/'results'/f'{key}.csv').open('w',newline='') as f:
                w=csv.writer(f);w.writerow(names);w.writerows(rows)
    assert all(row['violations']==0 for row in results['quality_checks']),results['quality_checks']
    # Independent standard-library recomputation from raw CSVs, without views/joins.
    with (ROOT/'data/orders.csv').open() as f:
        completed={int(o['order_id']) for o in csv.DictReader(f) if o['status']=='completed'}
    net=cost=0
    with (ROOT/'data/order_items.csv').open() as f:
        for row in csv.DictReader(f):
            if int(row['order_id']) not in completed: continue
            retained=int(row['quantity'])-int(row['returned_qty'])
            net+=retained*(int(row['unit_price_cents'])-int(row['discount_cents']))
            cost+=retained*int(row['unit_cost_cents'])
    k=results['01_kpis'][0]
    assert Decimal(str(k['net_sales_usd']))==Decimal(net)/100
    assert Decimal(str(k['gross_profit_usd']))==Decimal(net-cost)/100
    assert k['completed_orders']==len(completed)
    category_total=sum(Decimal(str(x['sales_usd'])) for x in results['07_category'])
    assert category_total==Decimal(net)/100
    report={'engine':f'DuckDB {duckdb.__version__}','counts':counts,'queries_executed':25,
            'quality_checks':results['quality_checks'],'independent_raw_csv_reconciliation':'PASS',
            'postgresql_native_execution':'Not executed in this environment'}
    (ROOT/'results/validation.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
    peak=max(results['02_monthly'],key=lambda x:x['net_sales_usd'])
    ret=results['10_returns'][0];repeat=results['18_repeat'][0];conc=results['25_concentration'][0]
    summary=f'''# Findings — synthetic retail simulation

Period: January 1, 2024–December 31, 2025. These describe generated data only.

| Metric | Result | Evidence |
|---|---:|---|
| Completed orders | {k['completed_orders']:,} | 01_kpis.csv |
| Net sales | ${k['net_sales_usd']:,.2f} | 01_kpis.csv |
| Gross profit | ${k['gross_profit_usd']:,.2f} | 01_kpis.csv |
| Average order value | ${k['aov_usd']:,.2f} | 01_kpis.csv |
| Gross margin | {k['gross_margin_pct']}% | 01_kpis.csv |
| Repeat customer share | {repeat['repeat_customer_pct']}% | 18_repeat.csv |
| Top buyer decile revenue share | {conc['top_decile_revenue_pct']}% | 25_concentration.csv |

1. The highest revenue month is **{peak['month']}**, at **${peak['net_sales_usd']:,.2f}**. Holiday demand was explicitly weighted in the generator; this is a demonstration of seasonal SQL, not evidence of actual Target seasonality.
2. **{ret['category_name']}** has the highest unit return rate, **{ret['unit_return_pct']}%**. Apparel's return probability was planted above the other categories. In a real project, investigate product quality, fit and return reasons before acting.
3. The top 10% of purchasing customers generate **{conc['top_decile_revenue_pct']}%** of revenue. Customer sampling weights intentionally create concentration. A real retailer could test a retention campaign, subject to consent and incremental margin measurement.

## Decision implications

Use revenue, margin and returns together when choosing category priorities. Store totals alone are insufficient: compare revenue per square foot, regional peers, channel mix and local demand. All stores exist for the full simulated period; revenue per square foot uses two years of revenue and includes digitally attributed sales.

RFM rules are illustrative fixed thresholds, not a validated customer model. Repeat share measures customers with two or more completed orders during the observation window, not retention probability. Month-one cohorts exclude December 2025 because a full follow-up month is unavailable. Observed customer spend is not predicted lifetime value.

## Validation and limits

All 25 analytical queries and 11 quality checks executed with DuckDB. Revenue, gross profit and completed orders were independently recomputed from raw CSVs using Python; category revenue reconciled to total revenue. PostgreSQL-native execution is not claimed. See [validation.json](validation.json) and the PostgreSQL setup instructions in the README.

No taxes, freight, labor, rent, customer acquisition costs, inventory snapshots or return timing are modeled. Gross profit is not operating profit. Returns are attached to original purchases and assumed fully recoverable. Discounts cannot establish promotion uplift without a causal design. Synthetic results must not be presented as Target business performance.
'''
    (ROOT/'results/analysis_summary.md').write_text(summary)
    print(json.dumps(report,indent=2,default=str))

if __name__=='__main__':run()
