"""Transparent volume-weighted paid chain ladder, in cents.

No actuarial libraries or hidden ultimate data are used by these functions.
Development age zero is the accident calendar year; age nine is the final age.
"""
import numpy as np
import pandas as pd

def validate_payments(payments, valuation_year):
    required={'claim_id','accident_year','line','development_age','payment_year','payment_cents'}
    if not required.issubset(payments.columns):
        raise ValueError('Missing payment fields')
    if payments[list(required)].isna().any().any():
        raise ValueError('Null payment fields')
    if payments.duplicated(['claim_id','development_age']).any():
        raise ValueError('Duplicate claim/development grain')
    if (payments.payment_cents<0).any() or (payments.payment_cents%1!=0).any():
        raise ValueError('Payments must be nonnegative integer cents')
    if not payments.development_age.between(0,9).all():
        raise ValueError('Development age outside 0–9')
    if (payments.payment_year!=payments.accident_year+payments.development_age).any():
        raise ValueError('Payment calendar inconsistent with development age')
    if (payments.payment_year>valuation_year).any():
        raise ValueError('Future payment leakage')

def build_triangle(payments, valuation_year):
    validate_payments(payments,valuation_year)
    if payments.empty:
        raise ValueError('Empty triangle input')
    origins = sorted(payments.accident_year.unique())
    totals=payments.groupby(['accident_year','development_age']).payment_cents.sum()
    incremental=pd.DataFrame(np.nan,index=pd.Index(origins,name='accident_year'),columns=range(10))
    for origin in origins:
        last=min(9,valuation_year-origin)
        if last<0: raise ValueError('Future accident year')
        for dev in range(last+1):
            incremental.loc[origin,dev]=totals.get((origin,dev),0)
    # Unknown future cells stay NaN, never zero. Row sums use observed ages only.
    cumulative=incremental.cumsum(axis=1)
    return incremental,cumulative

def development_factors(cumulative):
    rows=[]
    for dev in range(9):
        paired=cumulative[[dev,dev+1]].dropna()
        denom=paired[dev].sum()
        if paired.empty or denom<=0:
            raise ValueError(f'No credible positive denominator for age {dev}')
        factor=paired[dev+1].sum()/denom
        if factor<1: raise ValueError('Negative development is outside the fixture contract')
        rows.append({'from_age':dev,'to_age':dev+1,'factor':factor,
                     'paired_cohorts':len(paired),'denominator_cents':float(denom),
                     'numerator_cents':float(paired[dev+1].sum())})
    return pd.DataFrame(rows)

def project(cumulative, factors, tail_factor=1.0, excess_multiplier=1.0):
    if tail_factor<1 or excess_multiplier<0:
        raise ValueError('Tail must be >=1 and excess multiplier nonnegative')
    selected=1+(factors.factor.to_numpy()-1)*excess_multiplier
    complete=cumulative.copy()
    estimates=[]
    for origin,row in cumulative.iterrows():
        last=int(row.last_valid_index())
        paid=float(row[last])
        current=paid
        for dev in range(last,9):
            current*=selected[dev]
            complete.loc[origin,dev+1]=current
        ultimate=current*tail_factor
        estimates.append({'accident_year':int(origin),'latest_age':last,
                          'paid_cents':paid,'ultimate_estimate_cents':ultimate,
                          'outstanding_estimate_cents':ultimate-paid,
                          'age_to_ultimate_factor':ultimate/paid if paid else np.nan})
    return pd.DataFrame(estimates),complete

def forecast_cashflow(cumulative, projected, valuation_year):
    rows=[]
    for origin in cumulative.index:
        last=int(cumulative.loc[origin].last_valid_index())
        for dev in range(last+1,10):
            rows.append({'accident_year':int(origin),'development_age':dev,
                         'payment_year':int(origin+dev),
                         'predicted_payment_cents':float(projected.loc[origin,dev]-projected.loc[origin,dev-1])})
    return pd.DataFrame(rows,columns=['accident_year','development_age','payment_year','predicted_payment_cents'])

def fit_lines(payments,valuation_year):
    """Fit separate timing patterns; no pooled factor assumptions across lines."""
    artifacts={}
    for line in sorted(payments.line.unique()):
        inc,cum=build_triangle(payments.loc[payments.line==line],valuation_year)
        factors=development_factors(cum)
        estimates,complete=project(cum,factors)
        cashflow=forecast_cashflow(cum,complete,valuation_year)
        artifacts[line]={'incremental':inc,'cumulative':cum,'factors':factors,
                         'estimates':estimates,'projected':complete,'cashflow':cashflow}
    return artifacts
