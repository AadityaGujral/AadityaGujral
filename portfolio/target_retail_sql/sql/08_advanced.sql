-- query: 24_rolling
-- What is the trailing three-month average revenue?
WITH monthly AS (SELECT CAST(date_trunc('month',order_date) AS DATE) AS month,SUM(net_sales_cents)/100.0 AS sales_usd FROM order_totals GROUP BY 1) SELECT month,ROUND(sales_usd,2) AS sales_usd,CASE WHEN COUNT(*) OVER(ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)=3 THEN ROUND(AVG(sales_usd) OVER(ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW),2) END AS trailing_three_month_avg_usd FROM monthly ORDER BY month;

-- query: 25_concentration
-- What share of revenue comes from the top 10% of buyers?
WITH spend AS (SELECT customer_id,SUM(net_sales_cents) AS sales FROM order_totals GROUP BY customer_id), ranked AS (SELECT *,ROW_NUMBER() OVER(ORDER BY sales DESC,customer_id) AS position,COUNT(*) OVER() AS buyers FROM spend) SELECT ROUND(100.0*SUM(CASE WHEN position<=CEIL(buyers*.10) THEN sales ELSE 0 END)/SUM(sales),2) AS top_decile_revenue_pct FROM ranked;
