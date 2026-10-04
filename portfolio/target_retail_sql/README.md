# Target-Style Retail Analytics | SQL

**Aditya Gujral · Business Analytics Portfolio**

A reproducible retail case study that turns 120,000 synthetic orders into sales, product, store and customer insights using SQL. Built for a retail analytics manager deciding where to investigate margin pressure, customer concentration and store performance.

**Data disclosure:** This is an independent educational simulation inspired by big-box retail. It is not a Target database, is not affiliated with Target, and contains no real customer or proprietary data. All findings refer only to the generated dataset. Target's corporate site supplies general retail context; no company metrics were used to calibrate the simulation.

## At a glance

| Component | Scope |
|---|---|
| Period | January 2024–December 2025; 24 complete months |
| Orders / order lines | 120,000 / 360,012 |
| Customers / products / stores | 10,000 / 300 / 24 |
| SQL | 25 business queries, 11 quality checks, 2 reusable views |
| Techniques | Joins, CTEs, CASE, subqueries, NOT EXISTS, LAG, ROW_NUMBER, cumulative sums, rolling windows, cohort retention |
| Dialect / execution | PostgreSQL-oriented SQL; portable DuckDB runner tested |

## Results from the simulation

| Metric | Value |
|---|---:|
| Completed orders | 117,080 |
| Net sales | $38,180,937.46 |
| Gross profit | $11,648,328.70 |
| Average order value | $326.11 |
| Gross margin | 30.51% |
| Repeat purchasing customer share | 89.38% |
| Top 10% buyer revenue share | 51.69% |

See [findings and decision implications](results/analysis_summary.md), [query map](docs/business_questions.md) and [exported evidence](results/). These values are calculated outputs, not real Target performance.

## Run locally in five minutes

Requires Python 3.10 or newer. Open a terminal in this project directory:

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell alternative: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/generate_data.py
python scripts/run_analysis.py
```

The generator writes six CSV files; the runner loads a temporary in-memory relational database, executes the SQL files unchanged, exports 25 result tables and one quality table, and updates the findings and validation receipt. No credentials or paid services are needed. The CSV files can be imported into Power BI, Excel or PostgreSQL. The seed is fixed at `20261004`; the reference results were generated with Python 3.12.14 and DuckDB 1.5.6. Check your Python version when comparing exact regenerated fixtures.

## Run in PostgreSQL

Use an **empty dedicated database**; the schema script intentionally does not drop existing data. Install PostgreSQL and its `psql` client, generate the CSVs, then run from the project root:

```bash
# Example local connection; replace with your own database name/user.
psql -d retail_analytics -v ON_ERROR_STOP=1 -f sql/01_schema.sql
psql -d retail_analytics -v ON_ERROR_STOP=1 -f sql/02_load.psql
psql -d retail_analytics -v ON_ERROR_STOP=1 -f sql/03_views.sql
psql -d retail_analytics -v ON_ERROR_STOP=1 -f sql/09_quality_checks.sql
psql -d retail_analytics -v ON_ERROR_STOP=1 -f sql/04_sales.sql
psql -d retail_analytics -v ON_ERROR_STOP=1 -f sql/05_products.sql
psql -d retail_analytics -v ON_ERROR_STOP=1 -f sql/06_stores.sql
psql -d retail_analytics -v ON_ERROR_STOP=1 -f sql/07_customers.sql
psql -d retail_analytics -v ON_ERROR_STOP=1 -f sql/08_advanced.sql
```

Every quality-check violations count must be zero before interpreting results. Native PostgreSQL execution was unavailable in the authoring environment and has not been claimed as tested. The DuckDB runner executes all analytical SQL and enforces the quality assertions automatically.

## Data model and metric decisions

Orders reference one customer and one store. Each order has one to five line items, each referencing a product; products reference a category. Stores also receive digital-channel attribution. Anonymous customers are outside scope.

| Table | Grain | Key |
|---|---|---|
| customers | Registered synthetic customer | customer_id |
| stores | Fictional store | store_id |
| categories | Merchandise category | category_id |
| products | Fictional SKU | product_id |
| orders | Placed order, including cancellations | order_id |
| order_items | SKU line within an order | order_id + line_id |

Money is stored as integer **USD cents** to avoid floating-point accumulation in source amounts. `sales_lines` excludes cancelled orders. `order_totals` aggregates to the order grain before calculating AOV or customer frequency, preventing basket joins from inflating order counts.

- Net sales = retained units × (unit price − per-unit discount).
- COGS = retained units × purchase-time unit cost; gross profit = net sales − COGS.
- AOV = net sales / completed orders, including fully returned orders.
- Return rate = returned units / units sold on completed orders.
- Repeat customer share = buyers with ≥2 completed orders / all purchasing customers.
- RFM uses a fixed January 1, 2026 cutoff; all three dimensions feed the illustrative rules. See [definitions](docs/data_dictionary.md).
- Retention compares first completed purchase month with the next calendar month; December 2025 cohorts are excluded from month-one results.

## What makes this an analyst project

The analysis combines revenue with gross margin and returns, normalizes store sales by floor area, separates repeat purchasing from cohort retention, distinguishes observed spend from predicted lifetime value, and reconciles revenue independently against the CSV inputs. Recommendations are framed as investigations or experiments rather than causal claims.

## Synthetic assumptions and limitations

The generator increases November/December order probability, assigns heterogeneous store/customer weights, and gives Apparel a higher return probability. Category prices and margins are assumed. Products are sampled uniformly, so the relatively high AOV is a simulation artifact rather than a calibrated grocery-heavy retail basket. Customer concentration and repeat behavior are also consequences of the sampling design.

There are no inventory records, operating expenses, tax, freight, marketing exposure or return timestamps. Returned merchandise is assumed fully recoverable; refunds are assigned to the original purchase date. This cannot measure operating profit, stockout risk, predictive lifetime value, causal promotion uplift or actual Target performance. Cohort maturity, source grain and these limitations are preserved in the findings.

## Repository guide

- `scripts/generate_data.py`: deterministic raw-data generator.
- `sql/01_schema.sql` and `02_load.psql`: relational schema and PostgreSQL CSV loader.
- `sql/03_views.sql`: consistent line- and order-level metrics.
- `sql/04_sales.sql` through `08_advanced.sql`: 25 numbered business questions.
- `sql/09_quality_checks.sql`: data and reconciliation checks.
- `scripts/run_analysis.py`: execution, CSV exports and independent validation.
- `docs/`: business questions, data dictionary and sources.
- `results/`: actual query outputs, findings and validation evidence.

## Sources

- [Target Corporation](https://corporate.target.com/) — general case-study context only.
- [PostgreSQL window functions](https://www.postgresql.org/docs/current/tutorial-window.html) — window-function semantics.
- [PostgreSQL COPY](https://www.postgresql.org/docs/current/sql-copy.html) and [psql](https://www.postgresql.org/docs/current/app-psql.html) — loading CSVs.
- Local primary evidence: [generator](scripts/generate_data.py), [queries](sql/), [results](results/) and [validation](results/validation.json).

## Portfolio description

Developed a reproducible SQL retail analytics case study using 120,000 synthetic orders and 360,012 order lines; implemented 25 analyses covering revenue growth, margin, customer segmentation, cohort retention and store benchmarking, with 11 data-quality checks and independent CSV reconciliation.
