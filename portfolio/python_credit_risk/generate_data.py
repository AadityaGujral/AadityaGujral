"""Generate the synthetic collections dataset used across this portfolio."""
import numpy as np, pandas as pd
rng=np.random.default_rng(42); n=1500
df=pd.DataFrame({
"account_id":[f"A{i:05d}" for i in range(1,n+1)],
"portfolio":rng.choice(["Credit Card","Medical","Personal Loan","Auto"],n,p=[.4,.2,.25,.15]),
"collector":rng.choice(["Alex","Jordan","Taylor","Morgan","Casey","Riley"],n),
"original_balance":np.round(rng.uniform(500,25000,n),2),
"days_past_due":rng.integers(1,181,n),"contact_attempts":rng.integers(0,16,n),
"rpc_count":rng.integers(0,7,n),"monthly_income":np.round(rng.normal(5200,1800,n).clip(1500,15000),2),
"credit_score":rng.normal(650,75,n).clip(420,830).astype(int)})
risk=-2+.013*df.days_past_due+.10*df.contact_attempts-.004*(df.credit_score-600)-.00012*(df.monthly_income-4000)
df["default_flag"]=(rng.random(n)<1/(1+np.exp(-risk))).astype(int)
pay=(.55-.0017*df.days_past_due+.00055*(df.credit_score-550)+rng.normal(0,.13,n)).clip(0,.95)
df["amount_collected"]=np.round(df.original_balance*pay*(1-.45*df.default_flag),2)
df["current_balance"]=np.round((df.original_balance-df.amount_collected).clip(0),2)
df["settlement_flag"]=((df.amount_collected/df.original_balance>.55)&(rng.random(n)>.45)).astype(int)
df["promise_to_pay"]=((df.rpc_count>0)&(rng.random(n)>.38)).astype(int)
df["aging_bucket"]=pd.cut(df.days_past_due,[0,30,60,90,120,999],labels=["1-30","31-60","61-90","91-120","120+"]).astype(str)
df["snapshot_date"]="2026-09-30"
df.to_csv("data/credit_risk_accounts.csv",index=False)
print("Created",len(df),"synthetic accounts")
