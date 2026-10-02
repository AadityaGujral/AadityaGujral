"""Independently reconcile exported holdout metrics and scoring outputs."""
import json
import numpy as np
import pandas as pd
from generate_data import ROOT
out=ROOT/'outputs'
rows=pd.read_csv(out/'holdout_predictions.csv');metrics=pd.read_csv(out/'test_metrics.csv')
y=rows.future_90dpd.to_numpy()
for _,m in metrics.iterrows():
    p=rows[m['model'].lower().replace(' ','_')+'_probability']
    # Mann-Whitney rank identity, independent from sklearn ROC-AUC implementation.
    ranks=p.rank(method='average').to_numpy();n1=sum(y);n0=len(y)-n1
    auc=(sum(ranks[y==1])-n1*(n1+1)/2)/(n1*n0)
    assert abs(auc-m.roc_auc)<1e-12
    pred=p.to_numpy()>=m.threshold
    assert int(sum((y==1)&pred))==m.tp
    assert int(sum((y==0)&pred))==m.fp
    assert int(sum((y==1)&~pred))==m.fn
    assert int(sum((y==0)&~pred))==m.tn
scores=pd.read_csv(out/'risk_scores.csv')
assert len(scores)==500 and scores.account_id.is_unique
assert scores.risk_probability.between(0,1).all()
assert scores.risk_probability.is_monotonic_decreasing
assert not set(scores.account_id)&set(rows.account_id)
(out/'verification.json').write_text(json.dumps({'status':'passed','checks':['independent rank-based AUC for all three models','all exported confusion matrix counts','500 unique unlabeled scores','probability bounds','score ranking','score/test account disjointness']},indent=2)+'\n')
print('Independent output checks passed')
