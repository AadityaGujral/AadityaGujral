-- query: 18_repeat
-- What fraction of purchasing customers ordered at least twice?
WITH counts AS (SELECT customer_id,COUNT(*) AS n FROM order_totals GROUP BY customer_id) SELECT COUNT(*) AS purchasing_customers,SUM(CASE WHEN n>=2 THEN 1 ELSE 0 END) AS repeat_customers,ROUND(100.0*SUM(CASE WHEN n>=2 THEN 1 ELSE 0 END)/COUNT(*),2) AS repeat_customer_pct FROM counts;

-- query: 19_customer_value
-- Which customers have the highest observed net spend?
SELECT customer_id,COUNT(*) AS completed_orders,ROUND(SUM(net_sales_cents)/100.0,2) AS observed_spend_usd,MAX(order_date) AS last_order_date FROM order_totals GROUP BY customer_id ORDER BY observed_spend_usd DESC,customer_id LIMIT 20;

-- query: 20_rfm
-- How can customers be segmented using transparent RFM rules?
WITH metrics AS (SELECT customer_id,CAST(DATE '2026-01-01'-MAX(order_date) AS INTEGER) AS recency_days,COUNT(*) AS frequency,SUM(net_sales_cents) AS monetary_cents FROM order_totals GROUP BY customer_id), segments AS (SELECT *,CASE WHEN recency_days<=60 AND frequency>=10 AND monetary_cents>=100000 THEN 'Loyal active' WHEN recency_days>180 AND frequency>=5 AND monetary_cents>=50000 THEN 'At risk' WHEN frequency=1 THEN 'One purchase' ELSE 'Other' END AS segment FROM metrics) SELECT segment,COUNT(*) AS customers,ROUND(SUM(monetary_cents)/100.0,2) AS observed_spend_usd FROM segments GROUP BY segment ORDER BY observed_spend_usd DESC;

-- query: 21_nonbuyers
-- How many registered customers made no completed purchase?
SELECT COUNT(*) AS registered_nonbuyers FROM customers c WHERE NOT EXISTS (SELECT 1 FROM order_totals o WHERE o.customer_id=c.customer_id);

-- query: 22_purchase_gap
-- What is the average gap between purchases?
WITH gaps AS (SELECT customer_id,order_date-LAG(order_date) OVER(PARTITION BY customer_id ORDER BY order_date,order_id) AS days_since_prior FROM order_totals) SELECT ROUND(AVG(days_since_prior),2) AS mean_days_between_orders FROM gaps WHERE days_since_prior IS NOT NULL;

-- query: 23_cohort
-- What is month-one retention for mature first-purchase cohorts?
WITH firsts AS (SELECT customer_id,CAST(date_trunc('month',MIN(order_date)) AS DATE) AS cohort FROM order_totals GROUP BY customer_id), retained AS (SELECT DISTINCT f.customer_id,f.cohort FROM firsts f JOIN order_totals o ON f.customer_id=o.customer_id WHERE date_trunc('month',o.order_date)=f.cohort+INTERVAL '1 month') SELECT f.cohort,COUNT(*) AS cohort_customers,COUNT(r.customer_id) AS retained_month_one,ROUND(100.0*COUNT(r.customer_id)/COUNT(*),2) AS month_one_retention_pct FROM firsts f LEFT JOIN retained r ON f.customer_id=r.customer_id WHERE f.cohort<DATE '2025-12-01' GROUP BY f.cohort ORDER BY f.cohort;
