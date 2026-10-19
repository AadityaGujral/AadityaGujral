PRAGMA foreign_keys=ON;
CREATE TABLE dim_month(month_id INTEGER PRIMARY KEY, month_start TEXT NOT NULL UNIQUE);
CREATE TABLE dim_unit(unit_id INTEGER PRIMARY KEY, unit_name TEXT NOT NULL);
CREATE TABLE fact_plan(month_id INTEGER REFERENCES dim_month, unit_id INTEGER REFERENCES dim_unit,
 units INTEGER NOT NULL CHECK(units>0), price_cents INTEGER NOT NULL, cost_cents INTEGER NOT NULL,
 PRIMARY KEY(month_id,unit_id));
CREATE TABLE fact_actual(transaction_id INTEGER PRIMARY KEY, month_id INTEGER REFERENCES dim_month,
 unit_id INTEGER REFERENCES dim_unit, units INTEGER NOT NULL CHECK(units>0),
 price_cents INTEGER NOT NULL, cost_cents INTEGER NOT NULL);
CREATE VIEW variance_bridge AS
WITH a AS (SELECT month_id,unit_id,SUM(units) units,
 SUM(units*price_cents) revenue_cents,SUM(units*cost_cents) cost_cents
 FROM fact_actual GROUP BY month_id,unit_id)
SELECT p.month_id,p.unit_id,p.units budget_units,a.units actual_units,
 p.units*p.price_cents budget_revenue_cents,a.revenue_cents actual_revenue_cents,
 p.units*(p.price_cents-p.cost_cents) budget_margin_cents,
 a.revenue_cents-a.cost_cents actual_margin_cents,
 (a.units-p.units)*(p.price_cents-p.cost_cents) volume_effect_cents,
 a.revenue_cents-a.units*p.price_cents price_effect_cents,
 a.units*p.cost_cents-a.cost_cents cost_effect_cents
FROM fact_plan p JOIN a USING(month_id,unit_id);
