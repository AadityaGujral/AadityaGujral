-- Collections & Recovery Analytics (synthetic portfolio data)
SELECT COUNT(*) accounts, SUM(original_balance) placed_balance,
SUM(amount_collected) collected,
ROUND(100.0*SUM(amount_collected)/NULLIF(SUM(original_balance),0),2) recovery_rate_pct
FROM collections_accounts;

SELECT aging_bucket, COUNT(*) accounts, SUM(current_balance) outstanding_balance
FROM collections_accounts GROUP BY aging_bucket ORDER BY aging_bucket;

SELECT collector, COUNT(*) accounts, SUM(amount_collected) collected,
ROUND(100.0*SUM(amount_collected)/SUM(original_balance),2) recovery_rate_pct,
ROUND(100.0*SUM(CASE WHEN rpc_count>0 THEN 1 ELSE 0 END)/COUNT(*),2) rpc_rate_pct
FROM collections_accounts GROUP BY collector ORDER BY collected DESC;

WITH perf AS (
 SELECT collector, SUM(amount_collected) collected,
 SUM(amount_collected)/SUM(original_balance) recovery_rate
 FROM collections_accounts GROUP BY collector)
SELECT *, DENSE_RANK() OVER(ORDER BY recovery_rate DESC) recovery_rank FROM perf;

SELECT account_id,current_balance,
NTILE(4) OVER(ORDER BY current_balance DESC) exposure_quartile
FROM collections_accounts;

SELECT account_id, collector, current_balance,
ROUND(current_balance*(1+days_past_due/180.0)*(850-credit_score)/430.0,2) priority_score
FROM collections_accounts ORDER BY priority_score DESC;