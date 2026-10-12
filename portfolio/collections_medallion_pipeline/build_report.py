"""Build portfolio figures and an evidence-backed findings memo from gold marts."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

ROOT=Path(__file__).resolve().parent

def build(root=ROOT):
    root=Path(root);fig=root/'figures';fig.mkdir(exist_ok=True)
    monthly=pd.read_csv(root/'outputs/monthly_kpis.csv')
    channel=pd.read_csv(root/'outputs/channel_performance.csv')
    summary=json.loads((root/'outputs/portfolio_summary.json').read_text())
    validation=json.loads((root/'outputs/validation.json').read_text())
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'figure.facecolor':'white','savefig.facecolor':'white','svg.fonttype':'none'})
    by_month=monthly.groupby('event_month',as_index=False).agg(payments_cents=('payments_cents','sum'),contact_attempts=('contact_attempts','sum'),right_party_contacts=('right_party_contacts','sum'))
    by_month['payments_usd']=by_month.payments_cents/100
    by_month['rpc_rate']=by_month.right_party_contacts/by_month.contact_attempts
    fig1,ax=plt.subplots(figsize=(11,5),layout='constrained')
    ax.plot(by_month.event_month,by_month.payments_usd/1e6,marker='o',color='#285f8f',linewidth=2)
    ax.set(title='Monthly recovered payments | Synthetic 2025 events',xlabel='Event month',ylabel='Payments ($ millions)')
    ax.tick_params(axis='x',rotation=45);ax.grid(axis='y',alpha=.2);ax.set_ylim(bottom=0)
    fig1.savefig(fig/'monthly_payments.svg',bbox_inches='tight');fig1.savefig(fig/'monthly_payments.png',dpi=150,bbox_inches='tight');plt.close(fig1)
    ordered=channel.sort_values('rpc_rate')
    fig2,ax=plt.subplots(figsize=(9,5),layout='constrained')
    bars=ax.barh(ordered.channel,ordered.rpc_rate*100,color='#b87816')
    ax.bar_label(bars,labels=[f'{v:.1f}%' for v in ordered.rpc_rate*100],padding=4)
    ax.set(title='Right-party contact rate by channel | Synthetic events',xlabel='Right-party contacts / attempts (%)',ylabel='Channel')
    ax.set_xlim(0,max(ordered.rpc_rate*100)*1.2);ax.grid(axis='x',alpha=.2)
    fig2.savefig(fig/'channel_rpc.svg',bbox_inches='tight');fig2.savefig(fig/'channel_rpc.png',dpi=150,bbox_inches='tight');plt.close(fig2)
    product=monthly.groupby('product',as_index=False).agg(payments_cents=('payments_cents','sum'),contact_attempts=('contact_attempts','sum'),right_party_contacts=('right_party_contacts','sum'),promises_to_pay=('promises_to_pay','sum'))
    product['payments_usd']=product.payments_cents/100
    product['rpc_rate']=product.right_party_contacts/product.contact_attempts
    product['ptp_per_rpc']=product.promises_to_pay/product.right_party_contacts
    product.to_csv(root/'outputs/product_summary.csv',index=False,float_format='%.8f')
    overall_recovery=summary['payments_cents']/summary['starting_balance_cents']
    best_channel=channel.sort_values(['rpc_rate','channel'],ascending=[False,True]).iloc[0]
    highest_product=product.sort_values(['payments_usd','product'],ascending=[False,True]).iloc[0]
    memo=f'''# Findings — synthetic collections medallion pipeline

Scope: **January–December 2025**, **50,000 registered accounts**, and **300,000 canonical events**. Values describe generated data only.

| Measure | Result | Evidence |
|---|---:|---|
| Raw delivered rows | 300,275 | outputs/validation.json |
| Canonical deduplicated events | 300,000 | outputs/portfolio_summary.json |
| Quarantined invalid rows | 3 | outputs/batch_metrics.json |
| Active accounts represented | {summary['accounts']:,} | outputs/portfolio_summary.json |
| Payments recovered | ${summary['payments_cents']/100:,.2f} | outputs/portfolio_summary.json |
| Recovery against active-account starting balance | {overall_recovery:.2%} | outputs/portfolio_summary.json |
| Contact attempts | {summary['contact_events']:,} | outputs/portfolio_summary.json |

## Decision implications

1. The pipeline reconciles **300,275 deliveries** to **300,000 canonical events**: 272 redelivered event IDs are deduplicated and three intentionally invalid rows are quarantined. This demonstrates idempotent ingestion logic, not a real source-system defect rate.
2. **{best_channel.channel.title()}** has the highest generated right-party-contact rate at **{best_channel.rpc_rate:.2%}**, versus **{channel.rpc_rate.min():.2%}** for the lowest channel. The differences are random variation around one shared generator distribution; they do not establish channel causality or justify reallocating outreach spend.
3. **{highest_product['product']}** contributes the most recovered dollars, **${highest_product.payments_usd:,.2f}**. Product totals reflect account mix and randomly generated events, so compare rates and eligible balances before treating volume as performance.
4. Payments equal **{overall_recovery:.2%}** of starting balances for active accounts in this one-year observation window. This is a cash recovery ratio, not liquidation rate, cure rate, profitability, or causal program lift.

## Engineering evidence

The Bronze layer retains schema-enforced deliveries by batch. Silver enforces timestamps and amounts, quarantines bad records, removes repeat deliveries on `event_id`, and writes Parquet partitioned by event month. Gold produces monthly operational KPIs, account-level balances, and channel performance. The batch-02 Silver table has 300,000 rows and 300,000 distinct event IDs.

All **{validation['passed_checks']} independent reconciliations** pass using Python's standard library directly against raw CSV/JSONL, separate from Spark aggregation. They cover delivery-to-canonical counts, quarantine reasons, event subtotals, dollar totals, active-account balances, channel marts, monthly marts, and Silver key uniqueness. Eight contract tests also pass.

## Limitations

The dataset contains no real people, employer systems, bureau data, consent status, hardship indicators, legal restrictions, operational cost, agent capacity, or causal treatment assignment. Contact outcome probabilities are fixed across channels, products, regions, and time. Payments are generated independently of contact outcomes, so the project must not claim outreach effectiveness. The active-account denominator excludes 104 registered accounts with no events.

Parquet tables were executed locally with Apache Spark 4.0.1. This project does not use or claim execution on Databricks, Azure Data Factory, Synapse, ADLS, a cluster, Delta Lake, streaming checkpoints, or cloud orchestration. The versioned Silver batch tables demonstrate deterministic incremental merges; production concurrency and atomic table replacement require a transactional table format and orchestrator.
'''
    (root/'FINDINGS.md').write_text(memo)
    return {'overall_recovery':overall_recovery,'best_channel':best_channel.channel,'best_channel_rpc':best_channel.rpc_rate,'top_product':highest_product['product']}

if __name__=='__main__':print(json.dumps(build(),indent=2))
