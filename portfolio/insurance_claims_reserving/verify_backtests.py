"""Independently check holdout denominators and error metrics with CSV/Decimal."""
import csv
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def verify(root=ROOT):
    root=Path(root)
    actual=defaultdict(int)
    with (root/'data/observed_payments.csv').open() as f:
        for row in csv.DictReader(f):
            year=int(row['payment_year']);origin=int(row['accident_year'])
            for cutoff in [2023,2024]:
                if year==cutoff+1 and origin<=cutoff:
                    actual[(cutoff,row['line'],origin)]+=int(row['payment_cents'])
    with (root/'outputs/backtest_detail.csv').open() as f:
        detail=list(csv.DictReader(f))
    keys=[(int(r['training_cutoff']),r['line'],int(r['accident_year'])) for r in detail]
    assert len(keys)==len(set(keys)), 'Duplicate evaluated cohorts'
    assert set(keys)==set(actual), 'Holdout population mismatch'
    totals=defaultdict(lambda:[Decimal(0),Decimal(0),Decimal(0)])
    for key,row in zip(keys,detail):
        truth=Decimal(actual[key]);prediction=Decimal(row['predicted_payment_cents'])
        assert Decimal(row['actual_payment_cents'])==truth
        assert abs(Decimal(row['error_cents'])-(prediction-truth))<Decimal('.000001')
        values=totals[key[:2]]
        values[0]+=truth;values[1]+=prediction;values[2]+=abs(prediction-truth)
    with (root/'outputs/backtest_summary.csv').open() as f:
        for row in csv.DictReader(f):
            a,p,e=totals[(int(row['training_cutoff']),row['line'])]
            assert abs(Decimal(row['actual_payment_usd'])-a/100)<Decimal('.000001')
            assert abs(Decimal(row['predicted_payment_usd'])-p/100)<Decimal('.000001')
            assert abs(Decimal(row['wape_pct'])-100*e/a)<Decimal('.000001')
            assert abs(Decimal(row['bias_pct'])-100*(p-a)/a)<Decimal('.000001')
    numerator=sum(x[2] for x in totals.values());denominator=sum(x[0] for x in totals.values())
    report={'status':'PASS','method':'Python standard-library CSV + Decimal; no pandas aggregation',
            'checks':{'raw_csv_holdout_membership_and_amounts':True,'independent_wape_bias_denominators':True},
            'evaluated_line_origin_cells':len(detail),
            'pooled_absolute_error_usd':str(numerator/100),
            'pooled_actual_payment_usd':str(denominator/100),
            'pooled_wape_pct':str(100*numerator/denominator)}
    (root/'outputs/backtest_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':print(json.dumps(verify(),indent=2))
