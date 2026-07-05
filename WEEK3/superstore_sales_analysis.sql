/* ============================================================
   SUPERSTORE SALES ANALYSIS
   Subqueries, CTEs, and Window Functions
   Dataset: Sample - Superstore.csv (9,994 order lines)
   Tested against: SQLite 3.45 (also valid on PostgreSQL / MySQL with
   the minor notes at the bottom of this file)
   ============================================================ */


/* ============================================================
   STEP 1: SETUP DATA
   ============================================================ */

-- 1.1 Raw staging table -------------------------------------------------
DROP TABLE IF EXISTS superstore_raw;

CREATE TABLE superstore_raw (
    row_id          INTEGER,
    order_id        TEXT,
    order_date      TEXT,
    ship_date       TEXT,
    ship_mode       TEXT,
    customer_id     TEXT,
    customer_name   TEXT,
    segment         TEXT,
    country         TEXT,
    city            TEXT,
    state           TEXT,
    postal_code     TEXT,
    region          TEXT,
    product_id      TEXT,
    category        TEXT,
    sub_category    TEXT,
    product_name    TEXT,
    sales           REAL,
    quantity        INTEGER,
    discount        REAL,
    profit          REAL
);

-- Load the CSV (adjust for your engine):
-- SQLite:      .import --csv --skip 1 "Sample - Superstore.csv" superstore_raw
-- PostgreSQL:  \copy superstore_raw FROM 'Sample - Superstore.csv' DELIMITER ',' CSV HEADER;
-- MySQL:       LOAD DATA LOCAL INFILE 'Sample - Superstore.csv' INTO TABLE superstore_raw
--              FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS;


-- 1.2 Normalized tables ---------------------------------------------------
-- NOTE ON DESIGN: in this dataset, a customer_id maps 1:1 to customer_name
-- and segment, but NOT to city/state/region -- the same customer has
-- orders shipped to different addresses. So the customer dimension only
-- holds customer_id/name/segment; shipping geography stays on orders,
-- where it actually varies row to row.
-- Similarly, a handful of product_id values map to more than one
-- product_name/category combination in the raw data (data-entry
-- inconsistency in the source file), so product inserts use
-- INSERT OR IGNORE to keep product_id as a clean primary key while
-- still building the table from SELECT DISTINCT.

DROP TABLE IF EXISTS customers;
CREATE TABLE customers (
    customer_id    TEXT PRIMARY KEY,
    customer_name  TEXT,
    segment        TEXT
);

DROP TABLE IF EXISTS products;
CREATE TABLE products (
    product_id     TEXT PRIMARY KEY,
    product_name   TEXT,
    category       TEXT,
    sub_category   TEXT
);

DROP TABLE IF EXISTS orders;
CREATE TABLE orders (
    row_id         INTEGER PRIMARY KEY,
    order_id       TEXT,
    order_date     TEXT,
    ship_date      TEXT,
    ship_mode      TEXT,
    customer_id    TEXT REFERENCES customers(customer_id),
    product_id     TEXT REFERENCES products(product_id),
    country        TEXT,
    city           TEXT,
    state          TEXT,
    postal_code    TEXT,
    region         TEXT,
    sales          REAL,
    quantity       INTEGER,
    discount       REAL,
    profit         REAL
);


-- 1.3 Populate tables using SELECT DISTINCT -----------------------------

INSERT OR IGNORE INTO customers (customer_id, customer_name, segment)
SELECT DISTINCT customer_id, customer_name, segment
FROM superstore_raw;
-- (use plain INSERT ... SELECT DISTINCT on Postgres/MySQL -- they won't
--  hit duplicate customer_id conflicts in practice; SQLite's
--  INSERT OR IGNORE is just a safety net here)

INSERT OR IGNORE INTO products (product_id, product_name, category, sub_category)
SELECT DISTINCT product_id, product_name, category, sub_category
FROM superstore_raw;

INSERT INTO orders (row_id, order_id, order_date, ship_date, ship_mode,
                     customer_id, product_id, country, city, state, postal_code, region,
                     sales, quantity, discount, profit)
SELECT DISTINCT row_id, order_id, order_date, ship_date, ship_mode,
                customer_id, product_id, country, city, state, postal_code, region,
                sales, quantity, discount, profit
FROM superstore_raw;

-- Row counts after load: customers = 793, products = 1,862, orders = 9,994


/* ============================================================
   STEP 2: REQUIRED QUERIES
   ============================================================ */

-- 2.1 Orders where sales > average sales (Subquery) --------------------
SELECT row_id, order_id, customer_id, sales
FROM orders
WHERE sales > (SELECT AVG(sales) FROM orders)
ORDER BY sales DESC;


-- 2.2 Highest sales order for each customer (Subquery) ------------------
SELECT o.customer_id, c.customer_name, o.order_id, o.sales
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.sales = (
    SELECT MAX(o2.sales) FROM orders o2 WHERE o2.customer_id = o.customer_id
)
ORDER BY o.sales DESC;


-- 2.3 Total sales for each customer (CTE) --------------------------------
WITH customer_totals AS (
    SELECT c.customer_id, c.customer_name, SUM(o.sales) AS total_sales
    FROM customers c
    JOIN orders o ON o.customer_id = c.customer_id
    GROUP BY c.customer_id, c.customer_name
)
SELECT * FROM customer_totals
ORDER BY total_sales DESC;


-- 2.4 Customers whose total sales are above average (CTE + Subquery) ----
WITH customer_totals AS (
    SELECT c.customer_id, c.customer_name, SUM(o.sales) AS total_sales
    FROM customers c
    JOIN orders o ON o.customer_id = c.customer_id
    GROUP BY c.customer_id, c.customer_name
)
SELECT * FROM customer_totals
WHERE total_sales > (SELECT AVG(total_sales) FROM customer_totals)
ORDER BY total_sales DESC;


-- 2.5 Rank all customers based on total sales (Window Function) --------
WITH customer_totals AS (
    SELECT c.customer_id, c.customer_name, SUM(o.sales) AS total_sales
    FROM customers c
    JOIN orders o ON o.customer_id = c.customer_id
    GROUP BY c.customer_id, c.customer_name
)
SELECT customer_id, customer_name, total_sales,
       RANK() OVER (ORDER BY total_sales DESC) AS sales_rank
FROM customer_totals;


-- 2.6 Row number for each order within a customer (Window + PARTITION BY)
SELECT row_id, order_id, customer_id, order_date, sales,
       ROW_NUMBER() OVER (
           PARTITION BY customer_id
           ORDER BY order_date, row_id
       ) AS order_seq_num
FROM orders;


-- 2.7 Top 3 customers based on total sales (Window Function) -----------
WITH customer_totals AS (
    SELECT c.customer_id, c.customer_name, SUM(o.sales) AS total_sales
    FROM customers c
    JOIN orders o ON o.customer_id = c.customer_id
    GROUP BY c.customer_id, c.customer_name
),
ranked AS (
    SELECT customer_id, customer_name, total_sales,
           DENSE_RANK() OVER (ORDER BY total_sales DESC) AS sales_rank
    FROM customer_totals
)
SELECT * FROM ranked WHERE sales_rank <= 3;


/* ============================================================
   STEP 3: FINAL COMBINED QUERY
   Customer Name + Total Sales + Rank (JOIN + CTE + Window Function)
   ============================================================ */

WITH customer_totals AS (
    SELECT c.customer_id, c.customer_name, SUM(o.sales) AS total_sales
    FROM customers c
    JOIN orders o ON o.customer_id = c.customer_id
    GROUP BY c.customer_id, c.customer_name
)
SELECT ct.customer_name, ct.total_sales,
       RANK() OVER (ORDER BY ct.total_sales DESC) AS sales_rank
FROM customer_totals ct
ORDER BY sales_rank;


/* ============================================================
   MINI PROJECT: CUSTOMER SALES INSIGHTS
   ============================================================ */

-- 1) Top 5 customers -----------------------------------------------------
WITH customer_totals AS (
    SELECT c.customer_id, c.customer_name, SUM(o.sales) AS total_sales
    FROM customers c JOIN orders o ON o.customer_id = c.customer_id
    GROUP BY c.customer_id, c.customer_name
)
SELECT customer_name, total_sales FROM customer_totals
ORDER BY total_sales DESC LIMIT 5;


-- 2) Bottom 5 customers ---------------------------------------------------
WITH customer_totals AS (
    SELECT c.customer_id, c.customer_name, SUM(o.sales) AS total_sales
    FROM customers c JOIN orders o ON o.customer_id = c.customer_id
    GROUP BY c.customer_id, c.customer_name
)
SELECT customer_name, total_sales FROM customer_totals
ORDER BY total_sales ASC LIMIT 5;


-- 3) Customers who made only one order ------------------------------------
SELECT c.customer_id, c.customer_name, COUNT(DISTINCT o.order_id) AS order_count
FROM customers c JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name
HAVING COUNT(DISTINCT o.order_id) = 1
ORDER BY c.customer_name;


-- 4) Customers with above-average sales ------------------------------------
WITH customer_totals AS (
    SELECT c.customer_id, c.customer_name, SUM(o.sales) AS total_sales
    FROM customers c JOIN orders o ON o.customer_id = c.customer_id
    GROUP BY c.customer_id, c.customer_name
)
SELECT customer_name, total_sales FROM customer_totals
WHERE total_sales > (SELECT AVG(total_sales) FROM customer_totals)
ORDER BY total_sales DESC;


-- 5) Highest order value per customer ---------------------------------------
SELECT c.customer_name, MAX(o.sales) AS highest_order_value
FROM customers c JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_name
ORDER BY highest_order_value DESC;


/* ============================================================
   RESULTS SUMMARY (from running this script against
   Sample - Superstore.csv)
   ============================================================

   Row counts:            customers = 793 | products = 1,862 | orders = 9,994
   Total company sales:   $2,297,200.86
   Orders above average sales ($~230): 2,360 of 9,994
   Average customer total sales: $2,896.85
   Customers above average total sales: 294 (37.1%)
   Customers with exactly one order: 12
   Top 5 customers' combined sales: $88,281.80 (3.8% of total revenue)

   #1 customer overall: Sean Miller  -- total sales $25,043.05,
        driven by a single $22,638.48 order (a Canon copier) --
        the single largest order in the whole dataset.
   #2: Tamara Chand -- $19,052.22 total.
   #3: Raymond Buch -- $15,117.34 total.

   Full result tables are in "superstore_query_results.md".
   ============================================================ */


/* ============================================================
   ENGINE NOTES
   ============================================================
   - Written/tested on SQLite. RANK()/DENSE_RANK()/ROW_NUMBER() are
     standard ANSI window functions and work unchanged on PostgreSQL,
     MySQL 8+, and SQL Server.
   - LIMIT n works on SQLite/PostgreSQL/MySQL. On SQL Server, replace
     "... ORDER BY x LIMIT n" with "SELECT TOP n ... ORDER BY x".
   - INSERT OR IGNORE is SQLite syntax. Equivalent: PostgreSQL
     "INSERT ... ON CONFLICT DO NOTHING", MySQL "INSERT IGNORE".
   ============================================================ */
