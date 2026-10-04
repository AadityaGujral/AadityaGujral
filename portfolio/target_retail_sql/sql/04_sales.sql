-- query: 01_kpis
-- What are net sales, gross profit, AOV and gross margin?
SELECT COUNT(*) AS completed_orders, COUNT(DISTINCT customer_id) AS purchasing_customers, ROUND(SUM(net_sales_cents)/100.0,2) AS net_sales_usd, ROUND(SUM(net_sales_cents-cogs_cents)/100.0,2) AS gross_profit_usd, ROUND(AVG(net_sales_cents)/100.0,2) AS aov_usd, ROUND(100.0*SUM(net_sales_cents-cogs_cents)/NULLIF(SUM(net_sales_cents),0),2) AS gross_margin_pct FROM order_totals;

-- query: 02_monthly
-- How do monthly sales and MoM growth change?
WITH months AS (SELECT CAST(date_trunc('month',order_date) AS DATE) AS month, SUM(net_sales_cents) AS sales FROM order_totals GROUP BY 1), growth AS (SELECT *, LAG(sales) OVER(ORDER BY month) AS prior FROM months) SELECT month, ROUND(sales/100.0,2) AS net_sales_usd, ROUND(100.0*(sales-prior)/NULLIF(prior,0),2) AS mom_pct FROM growth ORDER BY month;

-- query: 03_channel
-- How do channels compare on orders, AOV and margin?
SELECT channel,COUNT(*) AS orders,ROUND(SUM(net_sales_cents)/100.0,2) AS net_sales_usd,ROUND(AVG(net_sales_cents)/100.0,2) AS aov_usd,ROUND(100.0*SUM(net_sales_cents-cogs_cents)/NULLIF(SUM(net_sales_cents),0),2) AS margin_pct FROM order_totals GROUP BY channel ORDER BY net_sales_usd DESC;

-- query: 04_yearly
-- What is year-over-year sales growth?
WITH years AS (SELECT EXTRACT(YEAR FROM order_date) AS year,SUM(net_sales_cents) AS sales FROM order_totals GROUP BY 1) SELECT year, ROUND(sales/100.0,2) AS sales_usd, ROUND(100.0*(sales-LAG(sales) OVER(ORDER BY year))/NULLIF(LAG(sales) OVER(ORDER BY year),0),2) AS yoy_pct FROM years ORDER BY year;

-- query: 05_discount
-- How do gross sales reconcile to net sales?
SELECT ROUND(SUM(gross_sales_cents)/100.0,2) AS gross_sales_usd,ROUND(SUM(discount_total_cents)/100.0,2) AS discounts_usd,ROUND(SUM(refund_cents)/100.0,2) AS refunds_usd,ROUND(SUM(net_sales_cents)/100.0,2) AS net_sales_usd FROM sales_lines;

-- query: 06_cancel
-- What share of orders was cancelled by channel?
SELECT channel, COUNT(*) AS placed_orders, ROUND(100.0*SUM(CASE WHEN status='cancelled' THEN 1 ELSE 0 END)/COUNT(*),2) AS cancellation_pct FROM orders GROUP BY channel ORDER BY channel;
