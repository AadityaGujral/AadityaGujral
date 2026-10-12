# Findings — synthetic collections medallion pipeline

Scope: **January–December 2025**, **50,000 registered accounts**, and **300,000 canonical events**. Values describe generated data only.

| Measure | Result | Evidence |
|---|---:|---|
| Raw delivered rows | 300,275 | outputs/validation.json |
| Canonical deduplicated events | 300,000 | outputs/portfolio_summary.json |
| Quarantined invalid rows | 3 | outputs/batch_metrics.json |
| Active accounts represented | 49,896 | outputs/portfolio_summary.json |
| Payments recovered | $25,298,590.35 | outputs/portfolio_summary.json |
| Recovery against active-account starting balance | 5.01% | outputs/portfolio_summary.json |
| Contact attempts | 216,627 | outputs/portfolio_summary.json |

## Decision implications

1. The pipeline reconciles **300,275 deliveries** to **300,000 canonical events**: 272 redelivered event IDs are deduplicated and three intentionally invalid rows are quarantined. This demonstrates idempotent ingestion logic, not a real source-system defect rate.
2. **Email** has the highest generated right-party-contact rate at **33.15%**, versus **32.91%** for the lowest channel. The differences are random variation around one shared generator distribution; they do not establish channel causality or justify reallocating outreach spend.
3. **Personal Loan** contributes the most recovered dollars, **$8,472,336.26**. Product totals reflect account mix and randomly generated events, so compare rates and eligible balances before treating volume as performance.
4. Payments equal **5.01%** of starting balances for active accounts in this one-year observation window. This is a cash recovery ratio, not liquidation rate, cure rate, profitability, or causal program lift.

## Engineering evidence

The Bronze layer retains schema-enforced deliveries by batch. Silver enforces timestamps and amounts, quarantines bad records, removes repeat deliveries on `event_id`, and writes Parquet partitioned by event month. Gold produces monthly operational KPIs, account-level balances, and channel performance. The batch-02 Silver table has 300,000 rows and 300,000 distinct event IDs.

All **12 independent reconciliations** pass using Python's standard library directly against raw CSV/JSONL, separate from Spark aggregation. They cover delivery-to-canonical counts, quarantine reasons, event subtotals, dollar totals, active-account balances, channel marts, monthly marts, and Silver key uniqueness. Eight contract tests also pass.

## Limitations

The dataset contains no real people, employer systems, bureau data, consent status, hardship indicators, legal restrictions, operational cost, agent capacity, or causal treatment assignment. Contact outcome probabilities are fixed across channels, products, regions, and time. Payments are generated independently of contact outcomes, so the project must not claim outreach effectiveness. The active-account denominator excludes 104 registered accounts with no events.

Parquet tables were executed locally with Apache Spark 4.0.1. This project does not use or claim execution on Databricks, Azure Data Factory, Synapse, ADLS, a cluster, Delta Lake, streaming checkpoints, or cloud orchestration. The versioned Silver batch tables demonstrate deterministic incremental merges; production concurrency and atomic table replacement require a transactional table format and orchestrator.
