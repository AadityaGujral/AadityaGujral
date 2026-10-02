"""Fictional account snapshots and 90-day outcomes, never employer data."""
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent
FEATURES=['days_past_due','credit_score','monthly_income','balance','utilization','missed_payments_6m','portfolio']
def generate(n=6000,seed=42,live=False):
    r=np.random.default_rng(seed)
    score=r.integers(420,821,n);dpd=r.integers(0,90,n)
    income=np.round(r.lognormal(8.4,.45,n),2);balance=np.round(r.uniform(500,25000,n),2)
    util=np.round(r.beta(3,2,n),4);missed=r.poisson(1.2,n)
    # Deliberately imperfect signal + unobserved shock: simulation, not an empirical model.
    z=-2.5+(650-score)/130+dpd/65+1.3*util+.3*missed+.35*np.log1p(balance/income)+r.normal(0,.8,n)
    event=r.binomial(1,1/(1+np.exp(-z)))
    snapshots=pd.to_datetime(['2026-06-30']*n) if live else pd.Timestamp('2025-01-01')+pd.to_timedelta(r.integers(0,365,n),unit='D')
    df=pd.DataFrame({'account_id':np.arange(10001 if live else 1,(10001 if live else 1)+n),'customer_id':np.arange(10001 if live else 1,(10001 if live else 1)+n),'snapshot_date':snapshots,'days_past_due':dpd,'credit_score':score,'monthly_income':income,'balance':balance,'utilization':util,'missed_payments_6m':missed,'portfolio':r.choice(['Credit Card','Auto','Personal Loan','Medical'],n)})
    if not live:
        df['outcome_end_date']=df.snapshot_date+pd.Timedelta(days=90)
        df['future_90dpd']=event
    # A small amount of missing income tests training-only imputation.
    df.loc[r.random(n)<.025,'monthly_income']=np.nan
    return df
if __name__=='__main__':
    (ROOT/'data').mkdir(exist_ok=True)
    generate().to_csv(ROOT/'data/historical_snapshots.csv',index=False)
    generate(500,84,True).to_csv(ROOT/'data/scoring_accounts.csv',index=False)
