-- Run in an empty, dedicated database. Amounts are integer USD cents.
CREATE TABLE categories(category_id INTEGER PRIMARY KEY, category_name VARCHAR(60) NOT NULL UNIQUE);
CREATE TABLE stores(store_id INTEGER PRIMARY KEY, store_name VARCHAR(60) NOT NULL, state VARCHAR(2) NOT NULL, region VARCHAR(20) NOT NULL, floor_sqft INTEGER NOT NULL CHECK(floor_sqft>0));
CREATE TABLE customers(customer_id INTEGER PRIMARY KEY, signup_date DATE NOT NULL, home_state VARCHAR(2) NOT NULL);
CREATE TABLE products(product_id INTEGER PRIMARY KEY, category_id INTEGER NOT NULL REFERENCES categories, product_name VARCHAR(80) NOT NULL, list_price_cents INTEGER NOT NULL CHECK(list_price_cents>0), unit_cost_cents INTEGER NOT NULL CHECK(unit_cost_cents>0));
CREATE TABLE orders(order_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers, store_id INTEGER NOT NULL REFERENCES stores, order_date DATE NOT NULL, channel VARCHAR(20) NOT NULL CHECK(channel IN ('store','pickup','delivery')), status VARCHAR(20) NOT NULL CHECK(status IN ('completed','cancelled')));
CREATE TABLE order_items(order_id INTEGER NOT NULL REFERENCES orders, line_id INTEGER NOT NULL, product_id INTEGER NOT NULL REFERENCES products, quantity INTEGER NOT NULL CHECK(quantity>0), returned_qty INTEGER NOT NULL CHECK(returned_qty>=0 AND returned_qty<=quantity), unit_price_cents INTEGER NOT NULL CHECK(unit_price_cents>0), unit_cost_cents INTEGER NOT NULL CHECK(unit_cost_cents>0), discount_cents INTEGER NOT NULL CHECK(discount_cents>=0 AND discount_cents<=unit_price_cents), PRIMARY KEY(order_id,line_id));
CREATE INDEX orders_customer_date ON orders(customer_id,order_date);
CREATE INDEX orders_store_date ON orders(store_id,order_date);
CREATE INDEX items_product ON order_items(product_id);
