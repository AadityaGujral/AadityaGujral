-- query: 07_category
-- Which categories contribute revenue and gross profit?
SELECT c.category_name,ROUND(SUM(s.net_sales_cents)/100.0,2) AS sales_usd,ROUND(SUM(s.net_sales_cents-s.cogs_cents)/100.0,2) AS gross_profit_usd,ROUND(100.0*SUM(s.net_sales_cents-s.cogs_cents)/NULLIF(SUM(s.net_sales_cents),0),2) AS margin_pct FROM sales_lines s JOIN categories c ON s.category_id=c.category_id GROUP BY c.category_name ORDER BY sales_usd DESC;

-- query: 08_top_products
-- Which ten products generate the most net sales?
SELECT p.product_name,SUM(s.quantity-s.returned_qty) AS retained_units,ROUND(SUM(s.net_sales_cents)/100.0,2) AS sales_usd FROM products p JOIN sales_lines s ON p.product_id=s.product_id GROUP BY p.product_id,p.product_name ORDER BY sales_usd DESC,p.product_id LIMIT 10;

-- query: 09_category_rank
-- What are the top three products within each category?
WITH p AS (SELECT category_id,product_id,SUM(net_sales_cents) AS sales FROM sales_lines GROUP BY category_id,product_id), ranked AS (SELECT *,ROW_NUMBER() OVER(PARTITION BY category_id ORDER BY sales DESC,product_id) AS rank FROM p) SELECT c.category_name,p.product_name,r.rank,ROUND(r.sales/100.0,2) AS sales_usd FROM ranked r JOIN products p ON r.product_id=p.product_id JOIN categories c ON r.category_id=c.category_id WHERE r.rank<=3 ORDER BY c.category_name,r.rank;

-- query: 10_returns
-- Which categories have the highest unit return rate?
SELECT c.category_name,SUM(s.quantity) AS sold_units,SUM(s.returned_qty) AS returned_units,ROUND(100.0*SUM(s.returned_qty)/SUM(s.quantity),2) AS unit_return_pct FROM sales_lines s JOIN categories c ON s.category_id=c.category_id GROUP BY c.category_name ORDER BY unit_return_pct DESC;

-- query: 11_pareto
-- How concentrated is product revenue?
WITH p AS (SELECT product_id,SUM(net_sales_cents) AS sales FROM sales_lines GROUP BY product_id) SELECT product_id,ROUND(sales/100.0,2) AS sales_usd,ROUND(100.0*SUM(sales) OVER(ORDER BY sales DESC,product_id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)/SUM(sales) OVER(),2) AS cumulative_sales_pct FROM p ORDER BY sales DESC,product_id;

-- query: 12_pairs
-- Which product pairs appear together most often?
SELECT a.product_id AS product_a,b.product_id AS product_b,COUNT(*) AS shared_orders FROM sales_lines a JOIN sales_lines b ON a.order_id=b.order_id AND a.product_id<b.product_id WHERE a.quantity>a.returned_qty AND b.quantity>b.returned_qty GROUP BY a.product_id,b.product_id HAVING COUNT(*)>=10 ORDER BY shared_orders DESC,product_a,product_b LIMIT 20;
