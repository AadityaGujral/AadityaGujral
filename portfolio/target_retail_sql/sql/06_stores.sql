-- query: 13_store
-- Which stores generate the most revenue per square foot?
SELECT s.store_id,s.store_name,s.state,s.floor_sqft,COUNT(o.order_id) AS orders,ROUND(COALESCE(SUM(o.net_sales_cents),0)/100.0,2) AS sales_usd,ROUND(COALESCE(SUM(o.net_sales_cents),0)/100.0/s.floor_sqft,2) AS sales_per_sqft_usd FROM stores s LEFT JOIN order_totals o ON s.store_id=o.store_id GROUP BY s.store_id,s.store_name,s.state,s.floor_sqft ORDER BY sales_per_sqft_usd DESC,s.store_id;

-- query: 14_region
-- Which regions have higher sales and margin?
SELECT s.region,COUNT(DISTINCT s.store_id) AS stores,ROUND(SUM(o.net_sales_cents)/100.0,2) AS sales_usd,ROUND(100.0*SUM(o.net_sales_cents-o.cogs_cents)/NULLIF(SUM(o.net_sales_cents),0),2) AS margin_pct FROM order_totals o JOIN stores s ON o.store_id=s.store_id GROUP BY s.region ORDER BY sales_usd DESC;

-- query: 15_store_peer
-- Which stores fall below regional revenue peers?
WITH totals AS (SELECT s.store_id,s.region,COALESCE(SUM(o.net_sales_cents),0) AS sales FROM stores s LEFT JOIN order_totals o ON s.store_id=o.store_id GROUP BY s.store_id,s.region), peers AS (SELECT *,AVG(sales) OVER(PARTITION BY region) AS regional_avg FROM totals) SELECT store_id,region,ROUND(sales/100.0,2) AS sales_usd,ROUND(regional_avg/100.0,2) AS regional_avg_usd FROM peers WHERE sales<regional_avg ORDER BY region,store_id;

-- query: 16_store_share
-- How much revenue does each store contribute?
SELECT store_id,ROUND(SUM(net_sales_cents)/100.0,2) AS sales_usd,ROUND(100.0*SUM(net_sales_cents)/SUM(SUM(net_sales_cents)) OVER(),2) AS sales_share_pct FROM order_totals GROUP BY store_id ORDER BY sales_usd DESC;

-- query: 17_state
-- How does net revenue compare by state?
SELECT s.state,COUNT(DISTINCT s.store_id) AS stores,ROUND(SUM(o.net_sales_cents)/100.0,2) AS sales_usd FROM stores s JOIN order_totals o ON s.store_id=o.store_id GROUP BY s.state ORDER BY sales_usd DESC;
