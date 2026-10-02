# Data dictionary

All identifiers are synthetic. Dates use ISO YYYY-MM-DD. Monetary values are integer cents.

| Table | Fields | Meaning |
|---|---|---|
| collectors | collector_id (PK), collector_name | Assigned or performing collector; ID 7 has no generated activity |
| customers | customer_id (PK), region, credit_score | Fictional region and score (constraint 300–850) |
| accounts | account_id (PK), customer_id (FK), collector_id (FK), portfolio | Account, owner, assigned collector and product |
| accounts | placed_date, original_balance_cents, days_past_due | Placement, positive placed balance, snapshot delinquency |
| payments | payment_id (PK), account_id (FK), payment_date, amount_cents | Positive posted receipt, dated between placement and snapshot |
| contact_attempts | contact_id (PK), account_id (FK), collector_id (FK), contact_date | Attempt, account, performing collector and date |
| contact_attempts | outcome | No answer, Wrong number, RPC or PTP |
| contact_attempts | promise_due_date, promise_amount_cents | Required for PTP; NULL for other outcomes |
| account_summary (view) | All account fields, region, credit_score, collector_name | Exactly one row per account |
| account_summary (view) | collected_cents, outstanding_cents, payment_count | Receipt sum, residual balance and receipt count; missing payments treated as zero |
| account_summary (view) | attempts, rpc_count, ptp_count, aging_bucket | Attempt count, RPC/PTP count, PTP count and ordered aging label |

The generator enforces cross-row payment reconciliation and dates in addition to database constraints. Amount and date consistency across multiple rows is checked by `build.py`; it is not enforced by a trigger. Names and region values are arbitrary fictional labels.
