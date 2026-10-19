# Finance Budget Variance & Contribution-Margin Model

Aditya Gujral | SQL, Python, dimensional modeling, Power BI-ready finance analytics

Why can revenue beat budget while margin misses it? This reproducible fictional services-business model answers that question with a cent-exact volume/price/cost bridge and separate facts at different grains. It adds multi-fact financial modeling to the existing retail SQL, insurance Python, and collections Spark portfolio.

## Run

Requires Python 3.10+ with its standard library; no packages, downloads, credentials, or database server needed.

```bash
cd portfolio/finance_variance_model
python run.py
python -m unittest -v test_project.py
```

`run.py` generates all inputs from seed 20261019, executes `schema.sql` in SQLite, validates results, writes four Power BI-importable JSON tables to ignored `generated/`, and refreshes compact evidence in `outputs/`. The database is in memory; existing repository files are not deleted. A rerun produces identical analytical outputs.

## Business questions and computed findings

The fictional period is January–December 2025, USD, three business units, 3,600 transaction lines and 36 monthly budget rows.

| Measure | Budget | Actual | Actual minus budget |
|---|---:|---:|---:|
| Revenue | $64,656,000.00 | $65,840,280.15 | +$1,184,280.15 |
| Contribution margin | $29,119,200.00 | $28,680,744.99 | -$438,455.01 |

The margin bridge reconciles exactly:

| Driver | Favorable / (unfavorable) |
|---|---:|
| Volume at budget unit margin | $472,528.00 |
| Realized price versus budget | $135,165.15 |
| Unit cost versus budget | ($1,046,148.16) |
| Total margin variance | ($438,455.01) |

Consumer accounts for $738,008.31 of the unfavorable cost effect and misses budget margin by $1,098,518.30. Enterprise contributes a $588,320.77 favorable margin variance; Partner contributes $71,742.52. In a real FP&A review, investigate Consumer cost drivers first, but these patterns are deliberately injected simulation assumptions—not evidence about real businesses or causal findings.

## Model and metric contract

| Table | Grain / key | Role |
|---|---|---|
| dim_month | one row per 2025 month; month_id | Shared month filter |
| dim_unit | one row per business unit; unit_id | Shared business-unit filter |
| fact_plan | one row per month/unit | Budget quantity and unit economics |
| fact_actual | one row per transaction_id | Actual quantity and unit economics |
| variance_bridge | one row per month/unit | Reconciled SQL comparison |

Plan is monthly while actual is transactional. Aggregate actual before joining plan, or use separate facts filtered by common dimensions. Do not join facts directly. The regression test demonstrates that the naive join repeats each budget row 100 times.

All financial calculations use integer cents until display. Margin means revenue less modeled variable costs, not EBITDA, net income, or cash flow. Positive effects are favorable. Per month/unit, with budget quantity Qb, actual quantity Qa, budget price Pb, and budget cost Cb:

- Volume = (Qa − Qb) × (Pb − Cb).
- Price = actual revenue − Qa × Pb.
- Cost = Qa × Cb − actual cost.
- Their sum = actual margin − budget margin.

Effects are calculated at month/unit grain then summed; do not use an unweighted average price or margin percentage at totals. This bridge allocates interactions using actual quantity for price/cost effects; it is one explicit decomposition convention, not a unique causal attribution. Volume includes mix shifts across business units; there is no separate mix effect.

## Power BI assembly (not executed here)

1. Generate the JSON files. In Power BI Desktop, create the `LoadTable` function from `power_query.m`, edit its folder path, and create queries named `dim_month`, `dim_unit`, `fact_plan`, and `fact_actual` by calling it with each table name.
2. Set all ID, units, price_cents and cost_cents columns to Whole Number; unit_name to Text; month_start to Date.
3. Create four active, single-direction one-to-many relationships: each dimension to each fact using its matching key. Never relate the two facts. `dim_month` is a month dimension, not a complete daily date table; do not mark it as a date table or apply daily time intelligence.
4. Add each measure in `measures.dax` separately. Format currency and percentages. Hide technical keys and raw per-unit numeric fields from report authors.
5. Build cards for revenue, margin and margin variance; a unit matrix with actual/budget margin; and month slicers from dimensions. For the bridge, import `outputs/bridge.json` separately as `variance_bridge`, connect the same dimensions, and sum its three effect columns divided by 100. Avoid relating it to either fact.
6. Check grand totals against this README and every month/unit against `outputs/bridge.json`. Test month/unit filters and blank-denominator behavior. DIVIDE returns blank for a zero denominator by default.

No PBIX, published dashboard, DAX engine execution, Power Query refresh, RLS, or rendered Power BI verification is claimed. SQLite/Python execution is validated; Power BI instructions require Desktop acceptance testing.

## Validation and evidence

The standard-library validator rereads generated in-memory source records, independently loops over all 36 cells, and compares nine SQL metrics per cell. It verifies totals, the exact bridge identity, foreign keys, uniqueness, budget completeness, duplicate/orphan rejection, and the fanout regression (11 checks). `test_project.py` additionally verifies repeatability and a hand-calculated bridge example with a negative variance.

- [Summary and unit findings](outputs/summary.json)
- [All 36 bridge cells](outputs/bridge.json)
- [Validation, runtime version and source hash](outputs/validation.json)
- [Test receipt](outputs/tests.json)

Scope: a complete synthetic grid with positive quantities; not a general production ingestion system. Missing actual months, cancellations, returns, multi-currency, tax, fixed costs, changing budget versions, and sparse-data policy require separate modeling. Constraints protect keys; they are not a comprehensive production data-quality framework.

## Provenance and assumptions

All data is original synthetic data generated by `run.py`; there are no employer/customer records or externally sourced datasets. Enterprise has an injected volume uplift, Consumer an injected cost increase, and Partner an injected price premium. The same seeded pseudorandom variation is used each run. Synthetic results demonstrate model behavior, not business performance. No real-world financial recommendation is intended.

## Sources

Official documentation reviewed October 19, 2026:

- [Microsoft: Star schema guidance](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema) — consistent fact grain, dimension keys, one-to-many relationships and explicit measures.
- [Microsoft: DIVIDE](https://learn.microsoft.com/en-us/dax/divide-function-dax) — safe denominator handling in the supplied measures.

The numerical evidence comes from the included generator and executed SQL, not from these documentation sources.
