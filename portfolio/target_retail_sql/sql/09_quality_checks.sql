-- query: quality_checks
-- Every violations count must equal zero. Failures block publication of results.
SELECT 'orders_without_lines' AS check_name,COUNT(*) AS violations FROM orders o WHERE NOT EXISTS(SELECT 1 FROM order_items i WHERE i.order_id=o.order_id)
UNION ALL SELECT 'purchase_before_signup',COUNT(*) FROM orders o JOIN customers c ON o.customer_id=c.customer_id WHERE o.order_date<c.signup_date
UNION ALL SELECT 'cancelled_returns',COUNT(*) FROM orders o JOIN order_items i ON o.order_id=i.order_id WHERE o.status='cancelled' AND i.returned_qty>0
UNION ALL SELECT 'orphan_customers',COUNT(*) FROM orders o LEFT JOIN customers c ON o.customer_id=c.customer_id WHERE c.customer_id IS NULL
UNION ALL SELECT 'orphan_stores',COUNT(*) FROM orders o LEFT JOIN stores s ON o.store_id=s.store_id WHERE s.store_id IS NULL
UNION ALL SELECT 'orphan_products',COUNT(*) FROM order_items i LEFT JOIN products p ON i.product_id=p.product_id WHERE p.product_id IS NULL
UNION ALL SELECT 'duplicate_products_in_basket',COUNT(*) FROM (SELECT order_id,product_id FROM order_items GROUP BY order_id,product_id HAVING COUNT(*)>1) d
UNION ALL SELECT 'missing_months',24-COUNT(DISTINCT date_trunc('month',order_date)) FROM orders
UNION ALL SELECT 'out_of_period',COUNT(*) FROM orders WHERE order_date<DATE '2024-01-01' OR order_date>DATE '2025-12-31'
UNION ALL SELECT 'order_grain_mismatch',ABS((SELECT COUNT(*) FROM orders WHERE status='completed')-(SELECT COUNT(*) FROM order_totals))
UNION ALL SELECT 'sales_reconciliation',ABS(SUM(gross_sales_cents-discount_total_cents-refund_cents-net_sales_cents)) FROM sales_lines;
