# Findings — synthetic retail simulation

Period: January 1, 2024–December 31, 2025. These describe generated data only.

| Metric | Result | Evidence |
|---|---:|---|
| Completed orders | 117,080 | 01_kpis.csv |
| Net sales | $38,180,937.46 | 01_kpis.csv |
| Gross profit | $11,648,328.70 | 01_kpis.csv |
| Average order value | $326.11 | 01_kpis.csv |
| Gross margin | 30.51% | 01_kpis.csv |
| Repeat customer share | 89.38% | 18_repeat.csv |
| Top buyer decile revenue share | 51.69% | 25_concentration.csv |

1. The highest revenue month is **2024-12-01**, at **$2,435,660.29**. Holiday demand was explicitly weighted in the generator; this is a demonstration of seasonal SQL, not evidence of actual Target seasonality.
2. **Apparel** has the highest unit return rate, **8.03%**. Apparel's return probability was planted above the other categories. In a real project, investigate product quality, fit and return reasons before acting.
3. The top 10% of purchasing customers generate **51.69%** of revenue. Customer sampling weights intentionally create concentration. A real retailer could test a retention campaign, subject to consent and incremental margin measurement.

## Decision implications

Use revenue, margin and returns together when choosing category priorities. Store totals alone are insufficient: compare revenue per square foot, regional peers, channel mix and local demand. All stores exist for the full simulated period; revenue per square foot uses two years of revenue and includes digitally attributed sales.

RFM rules are illustrative fixed thresholds, not a validated customer model. Repeat share measures customers with two or more completed orders during the observation window, not retention probability. Month-one cohorts exclude December 2025 because a full follow-up month is unavailable. Observed customer spend is not predicted lifetime value.

## Validation and limits

All 25 analytical queries and 11 quality checks executed with DuckDB. Revenue, gross profit and completed orders were independently recomputed from raw CSVs using Python; category revenue reconciled to total revenue. PostgreSQL-native execution is not claimed. See [validation.json](validation.json) and the PostgreSQL setup instructions in the README.

No taxes, freight, labor, rent, customer acquisition costs, inventory snapshots or return timing are modeled. Gross profit is not operating profit. Returns are attached to original purchases and assumed fully recoverable. Discounts cannot establish promotion uplift without a causal design. Synthetic results must not be presented as Target business performance.
