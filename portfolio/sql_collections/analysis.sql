-- Q01 Executive recovery KPIs (dollars)
SELECT COUNT(*) accounts, SUM(original_balance_cents)/100.0 placed, SUM(collected_cents)/100.0 collected, SUM(outstanding_cents)/100.0 outstanding, ROUND(100.0*SUM(collected_cents)/NULLIF(SUM(original_balance_cents),0),2) recovery_pct FROM account_summary;
-- Q02 Portfolio performance
SELECT portfolio, COUNT(*) accounts, SUM(collected_cents)/100.0 collected, ROUND(100.0*SUM(collected_cents)/SUM(original_balance_cents),2) recovery_pct FROM account_summary GROUP BY portfolio ORDER BY recovery_pct DESC;
-- Q03 Aging exposure
SELECT aging_bucket, COUNT(*) accounts, SUM(outstanding_cents)/100.0 outstanding FROM account_summary GROUP BY aging_bucket ORDER BY aging_bucket;
-- Q04 Collector rankings; account RPC coverage is distinct from contact RPC conversion
WITH perf AS (SELECT collector_id, collector_name, COUNT(*) accounts, SUM(collected_cents)/100.0 collected, 100.0*SUM(collected_cents)/SUM(original_balance_cents) recovery_pct, 100.0*SUM(rpc_count>0)/COUNT(*) rpc_account_pct FROM account_summary GROUP BY collector_id,collector_name)
SELECT *, DENSE_RANK() OVER(ORDER BY recovery_pct DESC) recovery_rank FROM perf;
-- Q05 Collectors with no activity retained through LEFT JOIN
SELECT k.collector_name, COUNT(c.contact_id) attempts, SUM(CASE WHEN c.outcome IN ('RPC','PTP') THEN 1 ELSE 0 END) rpc_contacts, ROUND(100.0*SUM(CASE WHEN c.outcome IN ('RPC','PTP') THEN 1 ELSE 0 END)/NULLIF(COUNT(c.contact_id),0),2) rpc_conversion_pct FROM collectors k LEFT JOIN contact_attempts c USING(collector_id) GROUP BY k.collector_id,k.collector_name;
-- Q06 Monthly receipts and cumulative receipts
WITH m AS (SELECT SUBSTR(payment_date,1,7) month, SUM(amount_cents)/100.0 collected FROM payments GROUP BY 1)
SELECT *, SUM(collected) OVER(ORDER BY month ROWS UNBOUNDED PRECEDING) cumulative_collected FROM m ORDER BY month;
-- Q07 Month over month change (NULL if no preceding month)
WITH m AS (SELECT SUBSTR(payment_date,1,7) month, SUM(amount_cents)/100.0 collected FROM payments GROUP BY 1), l AS (SELECT *, LAG(collected) OVER(ORDER BY month) previous FROM m)
SELECT *, ROUND(100.0*(collected-previous)/NULLIF(previous,0),2) growth_pct FROM l ORDER BY month;
-- Q08 Customers with multiple accounts: genuine customer/account JOIN
SELECT u.customer_id,u.region,COUNT(a.account_id) accounts,SUM(a.original_balance_cents)/100.0 placed FROM customers u INNER JOIN accounts a USING(customer_id) GROUP BY u.customer_id,u.region HAVING COUNT(*)>1 ORDER BY placed DESC;
-- Q09 Accounts with no payments (anti join)
SELECT a.account_id,a.portfolio,a.original_balance_cents/100.0 placed FROM accounts a LEFT JOIN payments p USING(account_id) WHERE p.payment_id IS NULL ORDER BY placed DESC;
-- Q10 Contacted but never reached
SELECT account_id,collector_name,attempts,outstanding_cents/100.0 outstanding FROM account_summary WHERE attempts>0 AND rpc_count=0 ORDER BY outstanding DESC;
-- Q11 Account RPC coverage by portfolio
SELECT portfolio,ROUND(100.0*SUM(rpc_count>0)/COUNT(*),2) rpc_account_pct,ROUND(SUM(collected_cents)/100.0/NULLIF(SUM(rpc_count),0),2) dollars_per_rpc_contact FROM account_summary GROUP BY portfolio;
-- Q12 Credit score segments (descriptive, not a trained risk model)
SELECT CASE WHEN credit_score<580 THEN 'High' WHEN credit_score<670 THEN 'Medium' ELSE 'Lower' END score_segment,COUNT(*) accounts,SUM(outstanding_cents)/100.0 outstanding FROM account_summary GROUP BY 1;
-- Q13 High exposure worklist
SELECT account_id,collector_name,outstanding_cents/100.0 outstanding,days_past_due,credit_score FROM account_summary WHERE outstanding_cents>=1000000 AND (days_past_due>90 OR credit_score<580) ORDER BY outstanding DESC LIMIT 25;
-- Q14 Exposure quartiles
SELECT account_id,outstanding_cents/100.0 outstanding,NTILE(4) OVER(ORDER BY outstanding_cents DESC,account_id) exposure_quartile FROM account_summary;
-- Q15 Latest contact, deterministic tie break
WITH ranked AS (SELECT *, ROW_NUMBER() OVER(PARTITION BY account_id ORDER BY contact_date DESC,contact_id DESC) rn FROM contact_attempts)
SELECT a.account_id,r.contact_date,r.outcome FROM accounts a LEFT JOIN ranked r ON a.account_id=r.account_id AND r.rn=1;
-- Q16 Regional recovery
SELECT region,COUNT(*) accounts,SUM(collected_cents)/100.0 collected,ROUND(100.0*SUM(collected_cents)/SUM(original_balance_cents),2) recovery_pct FROM account_summary GROUP BY region;
-- Q17 Placement cohort recovery to fixed snapshot (not comparable seasoning)
SELECT SUBSTR(placed_date,1,7) placement_month,COUNT(*) accounts,ROUND(100.0*SUM(collected_cents)/SUM(original_balance_cents),2) recovery_pct FROM account_summary GROUP BY 1 ORDER BY 1;
-- Q18 90+ DPD balance share: 90+ includes day 90
SELECT SUM(CASE WHEN days_past_due>=90 THEN outstanding_cents ELSE 0 END)/100.0 exposure_90_plus,ROUND(100.0*SUM(CASE WHEN days_past_due>=90 THEN outstanding_cents ELSE 0 END)/NULLIF(SUM(outstanding_cents),0),2) outstanding_share_pct FROM account_summary;
-- Q19 Due promises and illustrative fulfillment proxy
-- Only one promise/account in generated data; receipts between promise and due date.
WITH due AS (SELECT c.contact_id,c.account_id,c.promise_amount_cents,COALESCE(SUM(p.amount_cents),0) receipts_cents FROM contact_attempts c LEFT JOIN payments p ON p.account_id=c.account_id AND p.payment_date BETWEEN c.contact_date AND c.promise_due_date WHERE c.outcome='PTP' AND c.promise_due_date<='2026-06-30' GROUP BY c.contact_id,c.account_id,c.promise_amount_cents)
SELECT COUNT(*) due_promises,SUM(receipts_cents>=promise_amount_cents) fulfilled_proxy,ROUND(100.0*SUM(receipts_cents>=promise_amount_cents)/NULLIF(COUNT(*),0),2) fulfillment_proxy_pct FROM due;
-- Q20 Average time to first receipt
WITH first_payment AS (SELECT account_id,MIN(payment_date) first_date FROM payments GROUP BY account_id)
SELECT a.portfolio,COUNT(*) paid_accounts,ROUND(AVG(JULIANDAY(p.first_date)-JULIANDAY(a.placed_date)),1) mean_days_to_first_payment FROM accounts a INNER JOIN first_payment p USING(account_id) GROUP BY a.portfolio;
