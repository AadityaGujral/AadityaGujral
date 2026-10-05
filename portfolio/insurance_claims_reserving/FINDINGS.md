# Findings — synthetic insurance claims runoff

Valuation: **December 31, 2025**. Accident years: **2014–2025**. All amounts are undiscounted USD. No real insurer data is used.

| Measure | Calculated result | Evidence |
|---|---:|---|
| Simulated claims | 27,540 | data/generation_metadata.json |
| Observed paid amounts | $373,890,497.32 | outputs/reserve_summary.csv |
| Outstanding payment estimate | $138,951,826.71 | outputs/reserve_summary.csv |
| Estimated 2026 existing-claim cashflow | $43,115,338.32 | outputs/cashflow_summary.csv |
| Liability share of estimated outstanding | 73.79% | outputs/reserve_summary.csv |
| 2023–2025 accident-year reserve share | 76.42% | outputs/cohort_estimates.csv |
| Error versus hidden simulated outstanding | -0.07% | outputs/synthetic_truth_evaluation.csv |
| Pooled cell WAPE across two backtests | 1.88% | outputs/backtest_detail.csv |

## Business interpretation

1. Liability represents **73.79%** of the estimated outstanding payments despite only 35% expected claim allocation. Higher simulated severity and slower payment development are deliberately assigned to that line. In a real portfolio, use this concentration to prioritize line-specific reserve review, not as proof of adverse performance.
2. Forecast 2026 runoff is **$43,115,338.32**, or **31.03%** of base outstanding. This is an illustrative liquidity-planning input for existing claims only; new 2026 claims are excluded.
3. Increasing each development factor's excess above one by 5% raises outstanding to **$149,231,345.40**, a **7.40%** change. A separate 2% ultimate-tail scenario raises it to **$149,208,673.19**, adding **$10,256,846.48**. These are sensitivity assumptions, not confidence intervals or forecasts of real tail losses.
4. The combined calendar-holdout WAPE is **1.88%**, calculated as total absolute cohort forecast errors divided by total actual payments. The zero-future-payment baseline has 100% WAPE. Stable simulated development patterns make this a favorable test environment; there is no claim of comparable production accuracy.

## Validation and model scope

12 data/reconciliation checks and 8 analytical unit tests pass. Two further CSV/Decimal checks independently verify the historical holdout population and WAPE/bias calculations; see [backtest_verification.json](outputs/backtest_verification.json). Standard-library CSV sums independently reconcile paid amounts, development-factor numerators/denominators, and reserve products. Modeled future cashflow equals base outstanding. Forecasts fit observed cells only; 2024 and 2025 payment diagonals are hidden during their respective historical fits. Simulated ultimate truth is read only after current base forecasts exist.

The paid chain-ladder outstanding estimate is **ultimate minus paid**. Without case reserves or reporting dates, it cannot be separated into IBNR versus outstanding reported claims. The generated claim registry is complete at accident year, so there is no unreported-claim arrival process. No incurred triangle, earned premium, expense, reinsurance, discounting or capital modeling is present.

## Recommendation and limits

For this case study, keep separate development patterns by line, review recent Liability accident years, and use the runoff schedule alongside the deterministic stresses. A production implementation would need claim-reporting history, recovery/expense treatment, changing inflation and settlement patterns, empirical tail selection, and actuarial review before any booked reserve decision.

All simulated claims finish at development age nine, making a base tail of 1.00 valid **only by construction**. The +2% tail deliberately relaxes that assumption. Stable payment patterns, known population and a favorable severity process limit the backtest's external relevance. Reserve uncertainty is not quantified; no probability coverage, significance, adequacy or financial savings claim is made.
