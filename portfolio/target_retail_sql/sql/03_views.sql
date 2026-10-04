-- Completed orders only; returned units reduce both revenue and COGS.
-- Returned merchandise is assumed fully recoverable; no return-handling expense.
CREATE VIEW sales_lines AS
SELECT o.order_id,o.customer_id,o.store_id,o.order_date,o.channel,
 p.product_id,p.category_id,i.line_id,i.quantity,i.returned_qty,
 (i.quantity-i.returned_qty)*(i.unit_price_cents-i.discount_cents) AS net_sales_cents,
 (i.quantity-i.returned_qty)*i.unit_cost_cents AS cogs_cents,
 i.quantity*i.unit_price_cents AS gross_sales_cents,
 i.quantity*i.discount_cents AS discount_total_cents,
 i.returned_qty*(i.unit_price_cents-i.discount_cents) AS refund_cents
FROM orders o JOIN order_items i ON o.order_id=i.order_id
JOIN products p ON i.product_id=p.product_id WHERE o.status='completed';
-- One row per completed order, including fully returned orders at $0.
CREATE VIEW order_totals AS
SELECT order_id,customer_id,store_id,order_date,channel,
 SUM(net_sales_cents) AS net_sales_cents,SUM(cogs_cents) AS cogs_cents
FROM sales_lines GROUP BY order_id,customer_id,store_id,order_date,channel;
