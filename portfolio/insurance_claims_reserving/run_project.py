"""Rebuild synthetic data, estimate reserves, backtest and export evidence."""
import csv
import json
import platform
import hashlib
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.generate_data import generate, ROOT, VALUATION_YEAR
from src.reserving import fit_lines,project,build_triangle,development_factors

def concat_artifacts(artifacts,key):
    return pd.concat([a[key].assign(line=line) for line,a in artifacts.items()],ignore_index=True)

def backtest(payments):
    details=[]
    for cutoff in [2023,2024]:
        training=payments.loc[payments.payment_year<=cutoff].copy()
        fitted=fit_lines(training,cutoff)
        predictions=concat_artifacts(fitted,'cashflow')
        predictions=predictions.loc[predictions.payment_year==cutoff+1]
        # Only existing accident years are evaluated; new business is excluded.
        actual=payments.loc[(payments.payment_year==cutoff+1)&(payments.accident_year<=cutoff)]
        actual=actual.groupby(['line','accident_year']).payment_cents.sum().rename('actual_payment_cents').reset_index()
        predicted=predictions[['line','accident_year','predicted_payment_cents']]
        joined=actual.merge(predicted,on=['line','accident_year'],how='outer').fillna(0)
        joined['training_cutoff']=cutoff
        joined['evaluation_year']=cutoff+1
        joined['error_cents']=joined.predicted_payment_cents-joined.actual_payment_cents
        details.append(joined)
    detail=pd.concat(details,ignore_index=True)
    summaries=[]
    for (cutoff,line),group in detail.groupby(['training_cutoff','line']):
        actual=group.actual_payment_cents.sum();predicted=group.predicted_payment_cents.sum()
        summaries.append({'training_cutoff':int(cutoff),'evaluation_year':int(cutoff+1),'line':line,
                          'evaluated_cohorts':len(group),'actual_payment_usd':actual/100,
                          'predicted_payment_usd':predicted/100,
                          'bias_pct':100*(predicted-actual)/actual,
                          'wape_pct':100*group.error_cents.abs().sum()/actual,
                          'baseline_zero_payment_wape_pct':100.0})
    return detail,pd.DataFrame(summaries)

def independent_checks(root,payments,artifacts,estimates,cashflow):
    checks={}
    # Independent exact integer sums from source CSV, without pandas aggregation.
    by_line={};by_cell={};source_count=0
    with (root/'data/observed_payments.csv').open() as f:
        for r in csv.DictReader(f):
            source_count+=1;amount=int(r['payment_cents']);line=r['line']
            by_line[line]=by_line.get(line,0)+amount
            cell=(line,int(r['accident_year']),int(r['development_age']))
            by_cell[cell]=by_cell.get(cell,0)+amount
    checks['raw_csv_paid_reconciliation']=all(round(artifacts[line]['estimates'].paid_cents.sum())==amount for line,amount in by_line.items())
    checks['raw_csv_payment_count']=source_count==len(payments)
    factor_ok=True;reserve_ok=True
    for line,a in artifacts.items():
        for dev in range(9):
            eligible=[int(y) for y in a['cumulative'].index if y+dev+1<=VALUATION_YEAR]
            denom=sum(by_cell.get((line,y,k),0) for y in eligible for k in range(dev+1))
            numer=sum(by_cell.get((line,y,k),0) for y in eligible for k in range(dev+2))
            factor_ok &= abs(numer/denom-a['factors'].iloc[dev].factor)<1e-12
        # Pure Python factor product cross-check for each origin's unpaid estimate.
        for r in a['estimates'].itertuples():
            cumulative=sum(by_cell.get((line,r.accident_year,k),0) for k in range(r.latest_age+1))
            product=1.0
            for k in range(r.latest_age,9):product*=float(a['factors'].iloc[k].factor)
            reserve_ok &= abs(cumulative*(product-1)-r.outstanding_estimate_cents)<.01
    checks['independent_development_factor_reconciliation']=bool(factor_ok)
    checks['independent_reserve_product_reconciliation']=bool(reserve_ok)
    checks['future_cashflow_equals_base_reserve']=abs(cashflow.predicted_payment_cents.sum()-estimates.outstanding_estimate_cents.sum())<.01
    checks['nonnegative_reserve']=bool((estimates.outstanding_estimate_cents>=0).all())
    checks['observed_dates_only']=bool((payments.payment_year<=VALUATION_YEAR).all())
    checks['unknown_future_cells_preserved']=all(a['cumulative'].loc[2025,1:].isna().all() for a in artifacts.values())
    claims=pd.read_csv(root/'data/claims.csv')
    registry=payments.merge(claims,on='claim_id',suffixes=('_payment','_registry'),how='left',validate='many_to_one')
    checks['unique_registry_claims']=bool(claims.claim_id.is_unique)
    checks['registry_keys_and_attributes_match']=bool(registry.accident_year_registry.notna().all() and (registry.accident_year_payment==registry.accident_year_registry).all() and (registry.line_payment==registry.line_registry).all())
    truth=pd.read_csv(root/'data/evaluation_only/ultimate_truth.csv')
    future=pd.read_csv(root/'data/evaluation_only/future_payments.csv')
    # All simulated cents are accounted for across observed and hidden payments.
    checks['complete_simulation_cents_reconcile']=int(payments.payment_cents.sum())+int(future.payment_cents.sum())==int(truth.ultimate_cents.sum())
    checks['future_holdout_disjoint']=bool((future.payment_year>VALUATION_YEAR).all())
    if not all(checks.values()):raise AssertionError(checks)
    return {name:bool(value) for name,value in checks.items()}

def charts(root,artifacts,estimates,cashflow,bt):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'axes.titlesize':13,'figure.facecolor':'white','savefig.facecolor':'white',
                         'svg.fonttype':'none'})
    palette={'Auto':'#275E8E','Liability':'#B57918'}
    def save(fig,name):
        fig.savefig(root/'figures'/f'{name}.svg',bbox_inches='tight')
        fig.savefig(root/'figures'/f'{name}.png',dpi=150,bbox_inches='tight')
        plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(15,7),layout='constrained')
    cmap=plt.colormaps['Blues'].copy();cmap.set_bad('#e5e7eb')
    maximum=max(float(a['cumulative'].max().max()) for a in artifacts.values())/1e8
    for ax,(line,a) in zip(axes,artifacts.items()):
        values=a['cumulative'].to_numpy()/1e8
        image=ax.imshow(np.ma.masked_invalid(values),cmap=cmap,vmin=0,vmax=maximum,aspect='auto')
        ax.set_title(f'{line} — cumulative paid');ax.set_xlabel('Development age (0 = accident year)')
        ax.set_ylabel('Accident year');ax.set_xticks(range(10));ax.set_yticks(range(12),a['cumulative'].index)
        for i in range(12):
            for j in range(10):
                if np.isfinite(values[i,j]):ax.text(j,i,f'{values[i,j]:.1f}',ha='center',va='center',fontsize=8,color='white' if values[i,j]>maximum*.60 else '#1f2937')
    fig.colorbar(image,ax=axes,label='Cumulative paid ($ millions)',shrink=.78)
    fig.suptitle('Observed payment triangles at December 31, 2025 | Synthetic data\nGrey cells are unknown future payments; common color scale',fontsize=15)
    save(fig,'payment_triangles')
    pivot=estimates.pivot(index='accident_year',columns='line',values='outstanding_estimate_cents')/1e8
    fig,ax=plt.subplots(figsize=(11,5),layout='constrained')
    bottom=np.zeros(len(pivot))
    for line in pivot.columns:
        ax.bar(pivot.index,pivot[line],bottom=bottom,color=palette[line],label=line,edgecolor='white')
        bottom+=pivot[line].to_numpy()
    ax.set(title='Outstanding payment estimates by accident year | Dec. 31, 2025',xlabel='Accident year',ylabel='Estimated outstanding ($ millions)')
    ax.set_xticks(pivot.index);ax.set_ylim(bottom=0);ax.legend();ax.grid(axis='y',alpha=.2)
    save(fig,'reserves_by_cohort')
    pivot=cashflow.groupby(['payment_year','line']).predicted_payment_cents.sum().unstack(fill_value=0)/1e8
    fig,ax=plt.subplots(figsize=(11,5),layout='constrained');bottom=np.zeros(len(pivot))
    for line in pivot.columns:
        ax.bar(pivot.index,pivot[line],bottom=bottom,color=palette[line],label=line,edgecolor='white')
        bottom+=pivot[line].to_numpy()
    ax.set(title='Expected runoff cashflow for existing claims | Synthetic data',xlabel='Payment calendar year',ylabel='Predicted payments ($ millions)')
    ax.set_xticks(pivot.index);ax.set_ylim(bottom=0);ax.legend();ax.grid(axis='y',alpha=.2)
    save(fig,'runoff_cashflow')
    fig,ax=plt.subplots(figsize=(11,5),layout='constrained');x=np.arange(len(bt));w=.36
    ax.bar(x-w/2,bt.actual_payment_usd/1e6,w,color='#275E8E',label='Later observed payments')
    ax.bar(x+w/2,bt.predicted_payment_usd/1e6,w,color='#B57918',label='Forecast at prior year-end',hatch='//')
    ax.set_xticks(x,[f'{r.line}\n{r.training_cutoff} → {r.evaluation_year}' for r in bt.itertuples()])
    ax.set(title='Calendar holdout backtests | Prior accident years only',ylabel='Next-year payments ($ millions)')
    ax.set_ylim(bottom=0);ax.legend();ax.grid(axis='y',alpha=.2)
    save(fig,'backtest_payments')

def run(root=ROOT):
    root=Path(root)
    for name in ['outputs','figures']: (root/name).mkdir(exist_ok=True)
    metadata=generate(root)
    payments=pd.read_csv(root/'data/observed_payments.csv')
    artifacts=fit_lines(payments,VALUATION_YEAR)
    estimates=concat_artifacts(artifacts,'estimates')
    cashflow=concat_artifacts(artifacts,'cashflow')
    factors=concat_artifacts(artifacts,'factors')
    # Future truth is not read until all base forecasts are already created.
    truth=pd.read_csv(root/'data/evaluation_only/ultimate_truth.csv').groupby(['line','accident_year']).ultimate_cents.sum().rename('true_ultimate_cents').reset_index()
    evaluation=estimates.merge(truth,on=['line','accident_year'],validate='one_to_one')
    evaluation['true_outstanding_cents']=evaluation.true_ultimate_cents-evaluation.paid_cents
    evaluation['reserve_error_cents']=evaluation.outstanding_estimate_cents-evaluation.true_outstanding_cents
    summaries=[]
    for line,g in evaluation.groupby('line'):
        predicted=g.outstanding_estimate_cents.sum();actual=g.true_outstanding_cents.sum()
        summaries.append({'line':line,'paid_usd':g.paid_cents.sum()/100,
                          'ultimate_estimate_usd':g.ultimate_estimate_cents.sum()/100,
                          'outstanding_estimate_usd':predicted/100,
                          'synthetic_true_outstanding_usd':actual/100,
                          'reserve_bias_pct':100*(predicted-actual)/actual})
    summary=pd.DataFrame(summaries)
    bt_detail,bt_summary=backtest(payments)
    scenarios=[]
    for name,mult,tail in [('Base',1.0,1.0),('Development excess -5%',.95,1.0),('Development excess +5%',1.05,1.0),('Additional 2% ultimate tail',1.0,1.02)]:
        for line,a in artifacts.items():
            e,_=project(a['cumulative'],a['factors'],tail_factor=tail,excess_multiplier=mult)
            scenarios.append({'scenario':name,'line':line,'outstanding_estimate_usd':e.outstanding_estimate_cents.sum()/100})
    scenario=pd.DataFrame(scenarios)
    for name,df in [('cohort_estimates',estimates),('development_factors',factors),('cashflow_detail',cashflow),('reserve_summary',summary),('synthetic_truth_evaluation',evaluation),('backtest_detail',bt_detail),('backtest_summary',bt_summary),('sensitivity_scenarios',scenario)]:
        df.to_csv(root/'outputs'/f'{name}.csv',index=False,float_format='%.8f')
    for line,a in artifacts.items():
        a['incremental'].to_csv(root/'outputs'/f'{line.lower()}_incremental_triangle.csv',float_format='%.0f')
        a['cumulative'].to_csv(root/'outputs'/f'{line.lower()}_cumulative_triangle.csv',float_format='%.0f')
    cashflow.groupby(['payment_year','line']).predicted_payment_cents.sum().reset_index().to_csv(root/'outputs/cashflow_summary.csv',index=False,float_format='%.8f')
    checks=independent_checks(root,payments,artifacts,estimates,cashflow)
    from verify_backtests import verify
    backtest_verification=verify(root)
    suite=unittest.defaultTestLoader.discover(str(root/'tests'))
    test_result=unittest.TestResult()
    suite.run(test_result)
    if not test_result.wasSuccessful():
        raise AssertionError(test_result.errors+test_result.failures)
    versions={'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'matplotlib':matplotlib.__version__}
    report={'status':'PASS','data_checks':checks,'passed_data_checks':len(checks),
            'versions':versions,'seed':metadata['seed'],'valuation_date':'2025-12-31',
            'backtest_training_cutoffs':[2023,2024],'truth_used_for_estimation':False,
            'unit_tests':{'run':test_result.testsRun,'failures':len(test_result.failures),'errors':len(test_result.errors)},
            'independent_backtest_checks':backtest_verification['checks'],
            'input_sha256':{name:hashlib.sha256((root/'data'/name).read_bytes()).hexdigest() for name in ['claims.csv','observed_payments.csv']},
            'uncertainty':'Point estimates and deterministic scenarios only; no probabilistic interval'}
    (root/'outputs/validation.json').write_text(json.dumps(report,indent=2)+'\n')
    charts(root,artifacts,estimates,cashflow,bt_summary)
    total=summary.outstanding_estimate_usd.sum();paid=summary.paid_usd.sum()
    true=summary.synthetic_true_outstanding_usd.sum();bias=100*(total-true)/true
    next_year=cashflow.loc[cashflow.payment_year==2026].predicted_payment_cents.sum()/100
    liability=summary.loc[summary.line=='Liability','outstanding_estimate_usd'].iloc[0]
    newest=estimates.loc[estimates.accident_year>=2023].outstanding_estimate_cents.sum()/100
    tail=scenario.loc[scenario.scenario=='Additional 2% ultimate tail'].outstanding_estimate_usd.sum()
    high=scenario.loc[scenario.scenario=='Development excess +5%'].outstanding_estimate_usd.sum()
    wape=100*bt_detail.error_cents.abs().sum()/bt_detail.actual_payment_cents.sum()
    findings=f'''# Findings — synthetic insurance claims runoff

Valuation: **December 31, 2025**. Accident years: **2014–2025**. All amounts are undiscounted USD. No real insurer data is used.

| Measure | Calculated result | Evidence |
|---|---:|---|
| Simulated claims | {metadata['claims']:,} | data/generation_metadata.json |
| Observed paid amounts | ${paid:,.2f} | outputs/reserve_summary.csv |
| Outstanding payment estimate | ${total:,.2f} | outputs/reserve_summary.csv |
| Estimated 2026 existing-claim cashflow | ${next_year:,.2f} | outputs/cashflow_summary.csv |
| Liability share of estimated outstanding | {100*liability/total:.2f}% | outputs/reserve_summary.csv |
| 2023–2025 accident-year reserve share | {100*newest/total:.2f}% | outputs/cohort_estimates.csv |
| Error versus hidden simulated outstanding | {bias:+.2f}% | outputs/synthetic_truth_evaluation.csv |
| Pooled cell WAPE across two backtests | {wape:.2f}% | outputs/backtest_detail.csv |

## Business interpretation

1. Liability represents **{100*liability/total:.2f}%** of the estimated outstanding payments despite only 35% expected claim allocation. Higher simulated severity and slower payment development are deliberately assigned to that line. In a real portfolio, use this concentration to prioritize line-specific reserve review, not as proof of adverse performance.
2. Forecast 2026 runoff is **${next_year:,.2f}**, or **{100*next_year/total:.2f}%** of base outstanding. This is an illustrative liquidity-planning input for existing claims only; new 2026 claims are excluded.
3. Increasing each development factor's excess above one by 5% raises outstanding to **${high:,.2f}**, a **{100*(high/total-1):.2f}%** change. A separate 2% ultimate-tail scenario raises it to **${tail:,.2f}**, adding **${tail-total:,.2f}**. These are sensitivity assumptions, not confidence intervals or forecasts of real tail losses.
4. The combined calendar-holdout WAPE is **{wape:.2f}%**, calculated as total absolute cohort forecast errors divided by total actual payments. The zero-future-payment baseline has 100% WAPE. Stable simulated development patterns make this a favorable test environment; there is no claim of comparable production accuracy.

## Validation and model scope

{len(checks)} data/reconciliation checks and 8 analytical unit tests pass. Two further CSV/Decimal checks independently verify the historical holdout population and WAPE/bias calculations; see [backtest_verification.json](outputs/backtest_verification.json). Standard-library CSV sums independently reconcile paid amounts, development-factor numerators/denominators, and reserve products. Modeled future cashflow equals base outstanding. Forecasts fit observed cells only; 2024 and 2025 payment diagonals are hidden during their respective historical fits. Simulated ultimate truth is read only after current base forecasts exist.

The paid chain-ladder outstanding estimate is **ultimate minus paid**. Without case reserves or reporting dates, it cannot be separated into IBNR versus outstanding reported claims. The generated claim registry is complete at accident year, so there is no unreported-claim arrival process. No incurred triangle, earned premium, expense, reinsurance, discounting or capital modeling is present.

## Recommendation and limits

For this case study, keep separate development patterns by line, review recent Liability accident years, and use the runoff schedule alongside the deterministic stresses. A production implementation would need claim-reporting history, recovery/expense treatment, changing inflation and settlement patterns, empirical tail selection, and actuarial review before any booked reserve decision.

All simulated claims finish at development age nine, making a base tail of 1.00 valid **only by construction**. The +2% tail deliberately relaxes that assumption. Stable payment patterns, known population and a favorable severity process limit the backtest's external relevance. Reserve uncertainty is not quantified; no probability coverage, significance, adequacy or financial savings claim is made.
'''
    (root/'FINDINGS.md').write_text(findings)
    print(summary.round(2).to_string(index=False))
    print(f'Checks passed: {len(checks)}; total outstanding ${total:,.2f}; pooled backtest WAPE {wape:.2f}%')
    return report

if __name__=='__main__':run()
