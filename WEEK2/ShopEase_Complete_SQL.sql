-- NAME - SHRADDHA SANJAY WAKCHAURE 
-- SCOE

--  0: SCHEMA CREATION

CREATE TABLE IF NOT EXISTS customers (
    customer_id INT          PRIMARY KEY,
    first_name  VARCHAR(50)  NOT NULL,
    last_name   VARCHAR(50)  NOT NULL,
    email       VARCHAR(100) UNIQUE NOT NULL,
    city        VARCHAR(50)  NOT NULL,
    state       VARCHAR(50)  NOT NULL,
    join_date   DATE         NOT NULL,
    is_premium  BOOLEAN      DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_customers_city  ON customers(city);
CREATE INDEX IF NOT EXISTS idx_customers_state ON customers(state);

CREATE TABLE IF NOT EXISTS products (
    product_id   INT           PRIMARY KEY,
    product_name VARCHAR(100)  NOT NULL,
    category     VARCHAR(50)   NOT NULL,
    brand        VARCHAR(50)   NOT NULL,
    unit_price   DECIMAL(10,2) NOT NULL CHECK (unit_price > 0),
    stock_qty    INT           NOT NULL DEFAULT 0 CHECK (stock_qty >= 0)
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);

CREATE TABLE IF NOT EXISTS orders (
    order_id     INT           PRIMARY KEY,
    customer_id  INT           NOT NULL,
    order_date   DATE          NOT NULL,
    status       VARCHAR(20)   NOT NULL DEFAULT 'Pending'
                 CHECK (status IN ('Pending','Shipped','Delivered','Cancelled')),
    total_amount DECIMAL(12,2) NOT NULL CHECK (total_amount >= 0),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE INDEX IF NOT EXISTS idx_orders_date   ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

CREATE TABLE IF NOT EXISTS order_items (
    item_id      INT           PRIMARY KEY,
    order_id     INT           NOT NULL,
    product_id   INT           NOT NULL,
    quantity     INT           NOT NULL CHECK (quantity > 0),
    unit_price   DECIMAL(10,2) NOT NULL CHECK (unit_price > 0),
    discount_pct DECIMAL(5,2)  DEFAULT 0 CHECK (discount_pct BETWEEN 0 AND 100),
    FOREIGN KEY (order_id)   REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- 
--  0: SAMPLE DATA INSERTION
-- 

INSERT INTO customers VALUES
(101,'Aarav','Sharma','aarav.s@email.com','Mumbai','Maharashtra','2024-01-15',TRUE),
(102,'Priya','Patel','priya.p@email.com','Ahmedabad','Gujarat','2024-02-20',FALSE),
(103,'Rohan','Gupta','rohan.g@email.com','Delhi','Delhi','2024-03-10',TRUE),
(104,'Sneha','Reddy','sneha.r@email.com','Hyderabad','Telangana','2024-04-05',FALSE),
(105,'Vikram','Singh','vikram.s@email.com','Jaipur','Rajasthan','2024-05-12',TRUE),
(106,'Ananya','Iyer','ananya.i@email.com','Chennai','Tamil Nadu','2024-06-18',FALSE),
(107,'Karan','Mehta','karan.m@email.com','Pune','Maharashtra','2024-07-22',TRUE),
(108,'Divya','Nair','divya.n@email.com','Kochi','Kerala','2024-08-30',FALSE);

INSERT INTO products VALUES
(201,'Wireless Earbuds','Electronics','BoAt',1499.00,250),
(202,'Cotton T-Shirt','Clothing','Levis',799.00,500),
(203,'Smart Watch','Electronics','Noise',2999.00,150),
(204,'Running Shoes','Clothing','Nike',4599.00,120),
(205,'Bluetooth Speaker','Electronics','JBL',3499.00,200),
(206,'Bedsheet Set','Home','Spaces',1299.00,300),
(207,'Laptop Stand','Electronics','AmazonBasics',899.00,180),
(208,'Cushion Covers (Set)','Home','HomeCenter',599.00,400);

INSERT INTO orders VALUES
(1001,101,'2024-08-01','Delivered',4498.00),
(1002,102,'2024-08-03','Delivered',799.00),
(1003,103,'2024-08-05','Shipped',7498.00),
(1004,101,'2024-08-10','Delivered',3499.00),
(1005,104,'2024-08-12','Cancelled',2999.00),
(1006,105,'2024-08-15','Delivered',5898.00),
(1007,106,'2024-08-18','Pending',1299.00),
(1008,103,'2024-08-20','Delivered',899.00),
(1009,107,'2024-08-25','Shipped',6098.00),
(1010,108,'2024-08-28','Delivered',1598.00);

INSERT INTO order_items VALUES
(5001,1001,201,2,1499.00,0),(5002,1001,207,1,899.00,10),
(5003,1002,202,1,799.00,0),(5004,1003,203,1,2999.00,0),
(5005,1003,204,1,4599.00,5),(5006,1004,205,1,3499.00,0),
(5007,1005,203,1,2999.00,0),(5008,1006,201,1,1499.00,10),
(5009,1006,204,1,4599.00,5),(5010,1007,206,1,1299.00,0),
(5011,1008,207,1,899.00,0),(5012,1009,205,1,3499.00,0),
(5013,1009,208,2,599.00,15),(5014,1010,206,1,1299.00,0),
(5015,1010,208,1,599.00,0);


-- 
--  A: SQL BASICS
--  Q1 to Q6 — SELECT, Constraints, Primary Keys
-- 

-- Q1. Display all columns and rows from the customers table
SELECT * FROM customers;

-- Q2. Retrieve only first_name, last_name, and city of all customers
SELECT first_name, last_name, city
FROM customers;

-- Q3. List all unique categories available in the products table
SELECT DISTINCT category
FROM products;

-- Q4. Primary Keys of each table (informational — no SELECT needed)
-- customers  → customer_id (INT, PK)
-- products   → product_id  (INT, PK)
-- orders     → order_id    (INT, PK)
-- order_items→ item_id     (INT, PK)
-- A PK must be UNIQUE (identifies each row unambiguously) and NOT NULL
-- (a NULL identifier is meaningless and breaks FK references).

-- Q5. Constraints on the email column in customers
-- email VARCHAR(100) UNIQUE NOT NULL
-- UNIQUE  → no two customers may share an email address
-- NOT NULL → every customer must have an email
-- Attempting to insert a duplicate email raises:
--   ERROR: UNIQUE constraint failed: customers.email

-- Demonstration — this INSERT would FAIL:
-- INSERT INTO customers VALUES
-- (109,'Test','User','aarav.s@email.com','Bengaluru','Karnataka','2024-09-01',FALSE);

-- Q6. Inserting a product with unit_price = -50 (will FAIL due to CHECK)
-- The CHECK (unit_price > 0) constraint rejects negative prices.
-- INSERT INTO products VALUES
-- (209,'Broken Item','Electronics','NoName',-50.00,10);
-- ERROR: CHECK constraint failed: unit_price > 0


-- 
--  B: FILTERING & OPTIMIZATION
--  Q7 to Q12 — WHERE clauses, Indexes, SARGability
-- 

-- Q7. Retrieve all orders with status = 'Delivered'
SELECT *
FROM orders
WHERE status = 'Delivered';

-- Q8. Products in 'Electronics' category with unit_price > ₹2000
SELECT product_id, product_name, category, unit_price
FROM products
WHERE category = 'Electronics'
  AND unit_price > 2000;

-- Q9. Customers who joined in 2024 and belong to Maharashtra
--     Written in SARGable form (index-friendly range instead of YEAR())
SELECT *
FROM customers
WHERE join_date >= '2024-01-01'
  AND join_date <  '2025-01-01'
  AND state = 'Maharashtra';

-- Q10. Orders between 2024-08-10 and 2024-08-25, NOT Cancelled
SELECT *
FROM orders
WHERE order_date BETWEEN '2024-08-10' AND '2024-08-25'
  AND status <> 'Cancelled';

-- Q11. idx_orders_date: B-tree index enabling Index Range Scan on order_date.
--      Without it the engine reads every row (full table scan).
--      Sample query that USES this index:
SELECT order_id, customer_id, total_amount
FROM orders
WHERE order_date BETWEEN '2024-08-10' AND '2024-08-25';

-- Q12. Non-SARGable vs SARGable rewrite
--      BAD  (function wraps column — index on join_date is BYPASSED):
-- SELECT * FROM customers WHERE YEAR(join_date) = 2024;
--      GOOD (range predicate on raw column — index IS used):
SELECT *
FROM customers
WHERE join_date >= '2024-01-01'
  AND join_date <  '2025-01-01';


-- 
--  C: AGGREGATION
--  Q13 to Q18 — GROUP BY, SUM, COUNT, AVG, MIN, MAX, HAVING
-- 

-- Q13. Total number of orders
SELECT COUNT(*) AS total_orders
FROM orders;

-- Q14. Total revenue from all Delivered orders
SELECT SUM(total_amount) AS delivered_revenue
FROM orders
WHERE status = 'Delivered';

-- Q15. Average unit_price of products in each category
SELECT category,
       ROUND(AVG(unit_price), 2) AS avg_price
FROM products
GROUP BY category;

-- Q16. Order count and total revenue by status (sorted by revenue DESC)
SELECT status,
       COUNT(*)          AS order_count,
       SUM(total_amount) AS total_revenue
FROM orders
GROUP BY status
ORDER BY total_revenue DESC;

-- Q17. Most expensive and cheapest product in each category
SELECT category,
       MAX(unit_price) AS most_expensive,
       MIN(unit_price) AS cheapest
FROM products
GROUP BY category;

-- Q18. Categories where average unit_price > ₹2000 (HAVING clause)
SELECT category,
       ROUND(AVG(unit_price), 2) AS avg_price
FROM products
GROUP BY category
HAVING AVG(unit_price) > 2000;


-- 
--  D: JOINS & RELATIONSHIPS
--  Q19 to Q23 — INNER JOIN, LEFT JOIN, multi-table JOIN
-- 

-- Q19. Orders with customer first_name and last_name (INNER JOIN)
SELECT o.order_id,
       o.order_date,
       c.first_name,
       c.last_name,
       o.total_amount
FROM orders o
INNER JOIN customers c ON o.customer_id = c.customer_id;

-- Q20. All customers + their orders — customers with no orders show NULL (LEFT JOIN)
SELECT c.customer_id,
       c.first_name,
       c.last_name,
       o.order_id,
       o.order_date,
       o.total_amount
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id;

-- Q21. Order items with product details (3-table JOIN)
SELECT oi.order_id,
       p.product_name,
       oi.quantity,
       oi.unit_price,
       oi.discount_pct
FROM orders o
JOIN order_items oi ON o.order_id   = oi.order_id
JOIN products   p  ON oi.product_id = p.product_id;

-- Q22. LEFT vs RIGHT JOIN + FULL OUTER JOIN explanation
--      LEFT JOIN  → all rows from LEFT table (customers), NULLs where no match in orders
--      RIGHT JOIN → all rows from RIGHT table (orders), NULLs where no match in customers
--      FULL OUTER JOIN → all rows from both; NULLs on whichever side has no match
--      Use FULL OUTER JOIN for reconciliation / auditing both sides at once.

-- Q23. Foreign Key relationships:
--      orders.customer_id      → customers.customer_id
--      order_items.order_id    → orders.order_id
--      order_items.product_id  → products.product_id
-- Inserting customer_id = 999 (non-existent) raises:
--   ERROR: FOREIGN KEY constraint failed
-- INSERT INTO orders VALUES (1011, 999, '2024-09-01', 'Pending', 500.00);


-- 
--  E: ADVANCED CONCEPTS
--  Q24 to Q27 — CASE, ACID, Transactions
-- 

-- Q24. Classify products into price tiers using CASE
SELECT product_name,
       unit_price,
       CASE
           WHEN unit_price < 1000              THEN 'Budget'
           WHEN unit_price BETWEEN 1000 AND 3000 THEN 'Mid-Range'
           ELSE                                     'Premium'
       END AS price_tier
FROM products;

-- Q25. Count Delivered vs Not Delivered in a single row (CASE inside aggregate)
SELECT
    SUM(CASE WHEN status = 'Delivered' THEN 1 ELSE 0 END) AS delivered,
    SUM(CASE WHEN status <> 'Delivered' THEN 1 ELSE 0 END) AS not_delivered
FROM orders;

-- Q26. ACID Explanation (see README.md for full detail)
-- A = Atomicity   → all steps succeed or all are rolled back (no partial commits)
-- C = Consistency → DB moves from one valid state to another (constraints respected)
-- I = Isolation   → concurrent transactions don't see each other's mid-state
-- D = Durability  → committed data survives crashes (WAL / disk flush)

-- Q27. Complete atomic transaction — new order 1011 with 2 items + stock update
BEGIN;

    -- Step 1: Insert the new order
    INSERT INTO orders (order_id, customer_id, order_date, status, total_amount)
    VALUES (1011, 102, CURRENT_DATE, 'Pending', 2798.00);

    -- Step 2a: First order item — Wireless Earbuds (product 201, qty 1)
    INSERT INTO order_items (item_id, order_id, product_id, quantity, unit_price, discount_pct)
    VALUES (5016, 1011, 201, 1, 1499.00, 0);

    -- Step 2b: Second order item — Bedsheet Set (product 206, qty 1)
    INSERT INTO order_items (item_id, order_id, product_id, quantity, unit_price, discount_pct)
    VALUES (5017, 1011, 206, 1, 1299.00, 0);

    -- Step 3a: Deduct stock for Wireless Earbuds
    UPDATE products
    SET stock_qty = stock_qty - 1
    WHERE product_id = 201;

    -- Step 3b: Deduct stock for Bedsheet Set
    UPDATE products
    SET stock_qty = stock_qty - 1
    WHERE product_id = 206;

COMMIT;
-- If any step above fails, issue ROLLBACK to undo the entire transaction.


-- 
--  BONUS: ADDITIONAL BUSINESS QUERIES
-- 

-- BONUS 1. Top 3 customers by total spend
SELECT c.first_name,
       c.last_name,
       SUM(o.total_amount) AS total_spent
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.first_name, c.last_name
ORDER BY total_spent DESC
LIMIT 3;

-- BONUS 2. Net revenue per item (after discount)
SELECT oi.order_id,
       p.product_name,
       oi.quantity,
       oi.unit_price,
       oi.discount_pct,
       ROUND(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0), 2) AS net_revenue
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
ORDER BY net_revenue DESC;

-- BONUS 3. Data quality audit — row counts + NULL check per table
SELECT 'customers'   AS table_name, COUNT(*) AS row_count,
       SUM(CASE WHEN email        IS NULL THEN 1 ELSE 0 END) AS null_count FROM customers
UNION ALL
SELECT 'products',   COUNT(*),
       SUM(CASE WHEN product_name IS NULL THEN 1 ELSE 0 END) FROM products
UNION ALL
SELECT 'orders',     COUNT(*),
       SUM(CASE WHEN customer_id  IS NULL THEN 1 ELSE 0 END) FROM orders
UNION ALL
SELECT 'order_items',COUNT(*),
       SUM(CASE WHEN product_id   IS NULL THEN 1 ELSE 0 END) FROM order_items;

-- BONUS 4. Monthly revenue trend (works when data spans multiple months)
SELECT strftime('%Y-%m', order_date) AS month,   -- MySQL: DATE_FORMAT(order_date,'%Y-%m')
       COUNT(*)                       AS orders,
       SUM(total_amount)              AS revenue
FROM orders
WHERE status <> 'Cancelled'
GROUP BY month
ORDER BY month;

-- 
--  END OF SCRIPT
-- 
