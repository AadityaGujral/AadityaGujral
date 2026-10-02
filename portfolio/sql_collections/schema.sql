-- SQLite 3.25+; monetary amounts are integer cents.
PRAGMA foreign_keys = ON;
CREATE TABLE collectors (collector_id INTEGER PRIMARY KEY, collector_name TEXT NOT NULL UNIQUE);
CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, region TEXT NOT NULL, credit_score INTEGER NOT NULL CHECK(credit_score BETWEEN 300 AND 850));
CREATE TABLE accounts (account_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers, collector_id INTEGER NOT NULL REFERENCES collectors, portfolio TEXT NOT NULL, placed_date TEXT NOT NULL, original_balance_cents INTEGER NOT NULL CHECK(original_balance_cents > 0), days_past_due INTEGER NOT NULL CHECK(days_past_due >= 0));
CREATE TABLE payments (payment_id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts, payment_date TEXT NOT NULL, amount_cents INTEGER NOT NULL CHECK(amount_cents > 0));
CREATE TABLE contact_attempts (contact_id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts, collector_id INTEGER NOT NULL REFERENCES collectors, contact_date TEXT NOT NULL, outcome TEXT NOT NULL CHECK(outcome IN ('No answer','Wrong number','RPC','PTP')), promise_due_date TEXT, promise_amount_cents INTEGER, CHECK((outcome='PTP' AND promise_due_date IS NOT NULL AND promise_amount_cents > 0) OR (outcome<>'PTP' AND promise_due_date IS NULL AND promise_amount_cents IS NULL)));
CREATE INDEX idx_accounts_customer ON accounts(customer_id);
CREATE INDEX idx_accounts_collector ON accounts(collector_id);
CREATE INDEX idx_payments_account_date ON payments(account_id,payment_date);
CREATE INDEX idx_contacts_account_date ON contact_attempts(account_id,contact_date);
CREATE INDEX idx_contacts_collector ON contact_attempts(collector_id);
-- Aggregate each one-to-many fact BEFORE joining, preventing payment/contact fanout.
CREATE VIEW account_summary AS
WITH p AS (SELECT account_id, SUM(amount_cents) collected_cents, COUNT(*) payment_count FROM payments GROUP BY account_id),
c AS (SELECT account_id, COUNT(*) attempts, SUM(outcome IN ('RPC','PTP')) rpc_count, SUM(outcome='PTP') ptp_count FROM contact_attempts GROUP BY account_id)
SELECT a.*, u.region, u.credit_score, k.collector_name,
COALESCE(p.collected_cents,0) collected_cents,
a.original_balance_cents-COALESCE(p.collected_cents,0) outstanding_cents,
COALESCE(p.payment_count,0) payment_count, COALESCE(c.attempts,0) attempts,
COALESCE(c.rpc_count,0) rpc_count, COALESCE(c.ptp_count,0) ptp_count,
CASE WHEN days_past_due=0 THEN '0 Current' WHEN days_past_due<=30 THEN '1 1-30' WHEN days_past_due<=60 THEN '2 31-60' WHEN days_past_due<=90 THEN '3 61-90' WHEN days_past_due<=120 THEN '4 91-120' ELSE '5 121+' END aging_bucket
FROM accounts a INNER JOIN customers u USING(customer_id)
INNER JOIN collectors k USING(collector_id) LEFT JOIN p USING(account_id) LEFT JOIN c USING(account_id);
