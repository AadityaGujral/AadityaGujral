# Methodology, metric contract and business questions

## Decision and scope

A claims finance analyst needs a transparent estimate of outstanding payments and an existing-claim runoff schedule, with evidence of how the calculation performs on later payment diagonals. The case study is valued at December 31, 2025 and covers accident years 2014–2025. Estimates are undiscounted USD; raw source money is integer cents.

## Business questions

1. How much has been paid, and how much remains estimated outstanding by line?
2. Which accident years concentrate estimated outstanding payments?
3. How much existing-claim cashflow is forecast in 2026 and later years?
4. How do separate Auto and Liability development patterns differ?
5. How do historical one-year payment forecasts compare with held-out observations?
6. How sensitive are reserve estimates to development-factor and tail assumptions?

## Triangle construction

For accident year `i` and development age `j`, incremental paid is the sum of that year's payment cents, and cumulative paid `C[i,j]` is the sum from age zero through `j`. Age zero is the accident calendar year. Age nine is the last simulated payment age. Calendar year is accident year + development age.

Only cells with calendar year ≤ valuation year are observable. Observable cells with no payment contribute zero; future cells remain missing (`NaN`). The generator supplies one row at each observed age for every claim, including zero-cent amounts. The registry contains all generated claims; there is no reporting-delay process.

## Volume-weighted paid chain ladder

For each line and adjacent age pair:

`f[j] = sum(C[i,j+1]) / sum(C[i,j])`

Both sums use **only origins observed at both ages**. Including a newest cohort in the denominator without its next-age numerator would bias the factor. `development_factors.csv` retains each numerator, denominator and paired-cohort count. Later ages have fewer credible cohorts; no smoothing, credibility adjustment or hand-selection is used.

If the latest observable age is `k`:

`estimated ultimate[i] = C[i,k] × product(f[j], j=k..8) × tail`

`estimated outstanding[i] = estimated ultimate[i] − C[i,k]`

Future incremental cashflow is the difference between adjacent projected cumulative values. Base cashflow sums to base outstanding because the base tail is 1.00. No case reserves exist, so estimated outstanding cannot be separated into IBNR and outstanding reported claims.

## Historical backtesting

The model form is fixed before evaluation. For training cutoffs December 31, 2023 and December 31, 2024, fit using payments on or before the cutoff and predict next-calendar-year payments for existing accident years only. Payments from new accident years are excluded from both forecast and actual denominators. No final severity or later payment diagonal informs the fit.

Per-line and pooled metrics:

- Bias = (sum predicted − sum actual) / sum actual.
- WAPE = sum absolute origin-level errors / sum actual.
- Zero-future-payment baseline = 100% WAPE when actual runoff is positive.

WAPE is weighted by payment dollars, not a mean of percentages. The two historical evaluations overlap in accident-year membership and are not independent statistical samples. Their errors do not supply a confidence interval. The newest 2025 cohort has no complete one-year forward observation at the current valuation date.

Current reserve evaluation against hidden simulated ultimate is a separate diagnostic, **not** an observed real-world ultimate backtest. `synthetic_truth_evaluation.csv` provides the full error calculation after forecast creation.

## Deterministic sensitivities

Development scenarios replace each `f` with `1 + m × (f − 1)`, where `m` is 0.95 or 1.05. This changes the excess development above one, not the full factor by ±5%. A separate tail scenario multiplies estimated ultimate by 1.02; this also affects mature cohorts. The base generator has no payments beyond age nine, so the additional tail is hypothetical.

These scenarios are **not** bootstrap intervals, probability bounds, a stress calibration or a solvency capital calculation. Base runoff charts have no additional-tail cashflow timing because a timing assumption for post-age-nine payments was not supplied.

## Synthetic assumptions

Seed: 20261005. Annual volume rises from 1,800 to 2,790 claims. Expected line allocation is 65% Auto and 35% Liability. Median base severity is $6,500 Auto and $18,000 Liability, with lognormal sigma 0.85 and 3.5% accident-year severity inflation. Claim-level payment proportions follow a Dirichlet distribution centered on fixed line-specific patterns with concentration 90.

These are illustrative assumptions, not empirical insurer estimates. Timing patterns remain stable across cohorts, so historical forecasts have a favorable environment. Liability severity is deliberately higher and its development is deliberately slower. Integer-cent allocation uses largest fractional remainders so each claim's payments sum exactly to its simulated ultimate.

## Limitations and next steps

No case reserves, incurred losses, reporting delay, expense, reinsurance, deductibles, policy limits, salvage/subrogation, negative corrections, earned premium, investment discounting, calendar-year inflation shocks or new future accident years are modeled. No production reserve adequacy, causal change, significance, probability coverage or savings claim is made.

For real use, check changing settlement behavior and segmentation, select an empirical tail, quantify reserve uncertainty, add recoveries/expenses and case-reserve reconciliation, and obtain actuarial review. The base tail of 1.00 is justified only by this synthetic construction.

## Primary references

- [CAS Open Source Software: Chain Ladder tutorial](https://opensourcesoftware.casact.org/chain-ladder), including triangle construction and comparison with later development.
- [CAS Tail Factor Working Party, 2013: The Estimation of Loss Development Tail Factors](https://www.casact.org/sites/default/files/database/forum_13fforum_02-tail-factors-working-party.pdf), for development beyond the triangle's last credible maturity.
- [NumPy Generator.dirichlet](https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.dirichlet.html), for the synthetic payment-proportion generator.

Sources were checked October 5, 2026. Method formulas are implemented transparently in `src/reserving.py`; no external dataset or actuarial-library outputs are copied.
