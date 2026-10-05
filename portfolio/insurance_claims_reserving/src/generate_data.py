"""Generate fictional claim-level payment histories with exact cent allocation.

Future payments and final severities are held in a separate evaluation directory.
The forecasting functions receive only observed payments, never final severities.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261005
VALUATION_YEAR = 2025
PATTERNS = {
    'Auto': [.34, .27, .16, .09, .05, .035, .025, .015, .01, .005],
    'Liability': [.10, .16, .19, .17, .13, .09, .065, .045, .03, .02],
}

def generate(root=ROOT):
    root = Path(root)
    (root/'data/evaluation_only').mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    claims, payments = [], []
    claim_id = 0
    for year in range(2014, 2026):
        volume = 1800 + 90*(year-2014)
        for _ in range(volume):
            claim_id += 1
            line = 'Auto' if rng.random() < .65 else 'Liability'
            mean_log = np.log(6500 if line=='Auto' else 18000)
            # Cohort inflation affects severity, not the stable line-specific timing.
            ultimate = max(100, int(round(rng.lognormal(mean_log, .85)*1.035**(year-2014)*100)))
            proportions = rng.dirichlet(np.array(PATTERNS[line])*90)
            raw = ultimate*proportions
            cents = np.floor(raw).astype(np.int64)
            residual = ultimate-int(cents.sum())
            order = np.argsort(-(raw-cents), kind='stable')
            cents[order[:residual]] += 1
            claims.append((claim_id,year,line,ultimate))
            for dev,amount in enumerate(cents):
                payments.append((claim_id,year,line,dev,year+dev,int(amount)))
    truth = pd.DataFrame(claims, columns=['claim_id','accident_year','line','ultimate_cents'])
    all_payments = pd.DataFrame(payments, columns=['claim_id','accident_year','line','development_age','payment_year','payment_cents'])
    observed = all_payments.loc[all_payments.payment_year<=VALUATION_YEAR].copy()
    future = all_payments.loc[all_payments.payment_year>VALUATION_YEAR].copy()
    truth.drop(columns='ultimate_cents').to_csv(root/'data/claims.csv',index=False)
    observed.to_csv(root/'data/observed_payments.csv',index=False)
    truth.to_csv(root/'data/evaluation_only/ultimate_truth.csv',index=False)
    future.to_csv(root/'data/evaluation_only/future_payments.csv',index=False)
    metadata={'seed':SEED,'valuation_year':VALUATION_YEAR,'claims':len(truth),
              'observed_payment_rows':len(observed),'future_payment_rows':len(future),
              'accident_years':[2014,2025],'development_ages':[0,9],
              'assumed_mean_payment_patterns':PATTERNS,
              'distribution':'lognormal severity; Dirichlet payment proportions',
              'fully_synthetic':True,'development_beyond_age_9':False}
    (root/'data/generation_metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return metadata

if __name__=='__main__':
    print(json.dumps(generate(),indent=2))
