# Data dictionary and analytical contract

All records are fictional. Primary keys, foreign keys, non-null constraints and value checks are declared in `sql/01_schema.sql`.

| Table | Fields and meaning |
|---|---|
| categories | category_id; category_name (six merchandise groups) |
| stores | store_id; store_name; state (US abbreviation); region; floor_sqft (assumed retail area) |
| customers | customer_id (pseudonymous generated integer); signup_date; home_state |
| products | product_id; category_id; product_name; list_price_cents; unit_cost_cents |
| orders | order_id; customer_id; store_id (attribution store for every channel); order_date; channel (store/pickup/delivery); status (completed/cancelled) |
| order_items | order_id; line_id; product_id; quantity; returned_qty; unit_price_cents; unit_cost_cents; discount_cents (per unit, not line total) |

## Grain, timing and attribution

Each basket has unique product IDs. Returned quantity is either zero or the entire line quantity in this fixture. Order dates are calendar dates without timezones. Customer signup cannot follow their order. Stores are open throughout the period. Purchase-time price/cost fields live on line items to avoid historical restatement if a catalog changes.

Completed orders include fully returned baskets; cancellations have line items but contribute no sales. Purchase frequency and cohorts count completed orders even when fully returned. Retention is a calendar-month behavior measure, not a fixed 30-day measure.

MoM uses calendar monthly totals; all 24 months exist, verified by quality checks. The first month's growth is null. The trailing three-month mean is null until three months are present. Basket pairs count co-occurrence only for retained products; they are not association-rule lift or causal cross-sell evidence.

## RFM rule precedence

As of January 1, 2026, recency is days since last completed order, frequency is completed order count in the full two-year window, and monetary value is observed net sales in cents.

1. Loyal active: recency ≤60 days, frequency ≥10, spend ≥$1,000.
2. At risk: recency >180 days, frequency ≥5, spend ≥$500.
3. One purchase: frequency =1.
4. Other: remaining purchasing customers.

These are transparent demonstration thresholds, not optimized or externally validated segments. Registered nonbuyers are reported separately. Fixed rules avoid splitting tied recency values arbitrarily across quantiles.

## Reproduction and known design effects

Seed: 20261004. Holiday day weights: 1.65 in November/December versus 1 elsewhere. Store weights rise by store ID. Thirty percent of customer sampling is redirected to the earliest eligible 800 IDs. Apparel line return probability is 8%; other categories 2.5%. Return and cancellation realization vary around these expectations. No real distribution calibration was performed.
