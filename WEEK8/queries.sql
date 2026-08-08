-- =============================================================================
-- Part 3: SQL Analysis  (SQLite dialect)
-- Run against ecommerce.db, produced by load_to_sqlite.py
--
-- Revenue formula used throughout:
--     revenue = quantity * unit_price * (1 - discount_percent / 100.0)
-- NOTE: return rows (quantity < 0) naturally subtract from revenue when
-- included; several queries deliberately restrict to quantity > 0 where the
-- business question is about "purchases" rather than "net of returns" --
-- each query says which choice it makes.
-- =============================================================================


-- -----------------------------------------------------------------------
-- BASIC QUERIES
-- -----------------------------------------------------------------------

-- 1. Total revenue per category
SELECT
    p.category,
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)), 2) AS total_revenue
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.category
ORDER BY total_revenue DESC;


-- 2. Top 10 customers by total order value
SELECT
    o.customer_id,
    c.customer_name,
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)), 2) AS total_order_value
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
LEFT JOIN customers c ON c.customer_id = o.customer_id
WHERE o.customer_id IS NOT NULL
GROUP BY o.customer_id, c.customer_name
ORDER BY total_order_value DESC
LIMIT 10;


-- 3. Month-wise order count for the last 12 months
-- (relative to the most recent order_date present in the data, so the
--  query is reproducible regardless of when it's run)
WITH bounds AS (
    SELECT MAX(order_date) AS max_date FROM orders
)
SELECT
    strftime('%Y-%m', o.order_date) AS year_month,
    COUNT(DISTINCT o.order_id) AS order_count
FROM orders o, bounds b
WHERE o.order_date >= date(b.max_date, '-12 months')
GROUP BY year_month
ORDER BY year_month;


-- -----------------------------------------------------------------------
-- INTERMEDIATE QUERIES
-- -----------------------------------------------------------------------

-- 4. Customers who placed orders but never had any item delivered
--    ("delivered" = order.status = 'DELIVERED')
SELECT DISTINCT o.customer_id, c.customer_name
FROM orders o
LEFT JOIN customers c ON c.customer_id = o.customer_id
WHERE o.customer_id IS NOT NULL
  AND o.customer_id NOT IN (
      SELECT customer_id FROM orders WHERE status = 'DELIVERED' AND customer_id IS NOT NULL
  );


-- 5. Products that were ordered but had more returns than purchases
--    (purchases = rows with quantity > 0, returns = rows with quantity < 0,
--     compared by absolute unit count)
WITH item_flow AS (
    SELECT
        product_id,
        SUM(CASE WHEN quantity > 0 THEN quantity ELSE 0 END) AS units_purchased,
        SUM(CASE WHEN quantity < 0 THEN -quantity ELSE 0 END) AS units_returned
    FROM order_items
    GROUP BY product_id
)
SELECT
    p.product_id,
    p.product_name,
    f.units_purchased,
    f.units_returned
FROM item_flow f
JOIN products p ON p.product_id = f.product_id
WHERE f.units_returned > f.units_purchased
ORDER BY f.units_returned DESC;


-- 6. Return rate per category = returned items / total items (by unit count)
WITH item_flow AS (
    SELECT
        oi.product_id,
        SUM(CASE WHEN oi.quantity < 0 THEN -oi.quantity ELSE 0 END) AS units_returned,
        SUM(ABS(oi.quantity)) AS total_units
    FROM order_items oi
    GROUP BY oi.product_id
)
SELECT
    p.category,
    SUM(f.units_returned) AS total_returned,
    SUM(f.total_units) AS total_units,
    ROUND(100.0 * SUM(f.units_returned) / NULLIF(SUM(f.total_units), 0), 2) AS return_rate_percent
FROM item_flow f
JOIN products p ON p.product_id = f.product_id
GROUP BY p.category
ORDER BY return_rate_percent DESC;


-- -----------------------------------------------------------------------
-- ADVANCED QUERIES (Window Functions, CTEs, Subqueries)
-- -----------------------------------------------------------------------

-- 7. Running total of revenue per region, ordered by date
WITH daily_region_revenue AS (
    SELECT
        o.region_code,
        date(o.order_date) AS order_day,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS daily_revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    GROUP BY o.region_code, date(o.order_date)
)
SELECT
    region_code,
    order_day AS order_date,
    ROUND(daily_revenue, 2) AS daily_revenue,
    ROUND(SUM(daily_revenue) OVER (
        PARTITION BY region_code ORDER BY order_day
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ), 2) AS running_total
FROM daily_region_revenue
ORDER BY region_code, order_day;


-- 8. Rank products by total revenue within each category (ties share rank ->
--    RANK, not ROW_NUMBER, since RANK leaves gaps like DENSE_RANK avoids;
--    task says "same revenue should have same rank", RANK() satisfies this)
WITH product_revenue AS (
    SELECT
        p.category,
        p.product_name,
        p.product_id,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS total_revenue
    FROM order_items oi
    JOIN products p ON p.product_id = oi.product_id
    GROUP BY p.category, p.product_id, p.product_name
)
SELECT
    category,
    product_name,
    ROUND(total_revenue, 2) AS total_revenue,
    RANK() OVER (PARTITION BY category ORDER BY total_revenue DESC) AS rank_in_category
FROM product_revenue
ORDER BY category, rank_in_category;


-- 9. LAG/LEAD Analysis: days between consecutive orders per customer;
--    flag customers with average gap > 30 days as "At Risk"
WITH customer_orders AS (
    SELECT DISTINCT customer_id, order_date
    FROM orders
    WHERE customer_id IS NOT NULL
),
gaps AS (
    SELECT
        customer_id,
        order_date,
        LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date) AS previous_order_date
    FROM customer_orders
),
gaps_with_days AS (
    SELECT
        customer_id,
        order_date,
        previous_order_date,
        CASE WHEN previous_order_date IS NOT NULL
             THEN CAST(julianday(order_date) - julianday(previous_order_date) AS INTEGER)
             ELSE NULL END AS days_gap
    FROM gaps
),
customer_avg_gap AS (
    SELECT customer_id, AVG(days_gap) AS avg_gap
    FROM gaps_with_days
    WHERE days_gap IS NOT NULL
    GROUP BY customer_id
)
SELECT
    g.customer_id,
    g.order_date,
    g.previous_order_date,
    g.days_gap,
    CASE WHEN a.avg_gap > 30 THEN 'At Risk' ELSE 'Healthy' END AS risk_flag
FROM gaps_with_days g
LEFT JOIN customer_avg_gap a ON a.customer_id = g.customer_id
ORDER BY g.customer_id, g.order_date;


-- 10. CTE with Multiple Levels: monthly revenue per customer -> categorize
--     (High >10000 / Medium 5000-10000 / Low <5000) -> count per category per month
WITH monthly_customer_revenue AS (
    SELECT
        o.customer_id,
        strftime('%Y-%m', o.order_date) AS year_month,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS monthly_revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.customer_id IS NOT NULL
    GROUP BY o.customer_id, year_month
),
categorized AS (
    SELECT
        customer_id,
        year_month,
        monthly_revenue,
        CASE
            WHEN monthly_revenue > 10000 THEN 'High'
            WHEN monthly_revenue >= 5000 THEN 'Medium'
            ELSE 'Low'
        END AS revenue_category
    FROM monthly_customer_revenue
)
SELECT
    year_month,
    revenue_category,
    COUNT(DISTINCT customer_id) AS customer_count
FROM categorized
GROUP BY year_month, revenue_category
ORDER BY year_month, revenue_category;


-- 11. NTILE for Segmentation: quartiles by total lifetime value
WITH customer_ltv AS (
    SELECT
        o.customer_id,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS total_value
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.customer_id IS NOT NULL
    GROUP BY o.customer_id
),
quartiled AS (
    SELECT
        customer_id,
        total_value,
        NTILE(4) OVER (ORDER BY total_value DESC) AS quartile
    FROM customer_ltv
)
SELECT
    customer_id,
    ROUND(total_value, 2) AS total_value,
    quartile,
    CASE quartile
        WHEN 1 THEN 'Platinum'
        WHEN 2 THEN 'Gold'
        WHEN 3 THEN 'Silver'
        WHEN 4 THEN 'Bronze'
    END AS quartile_label
FROM quartiled
ORDER BY quartile, total_value DESC;


-- 12. Year-over-Year Comparison: each month's revenue vs same month prior year
WITH monthly_revenue AS (
    SELECT
        CAST(strftime('%Y', o.order_date) AS INTEGER) AS year,
        CAST(strftime('%m', o.order_date) AS INTEGER) AS month,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    GROUP BY year, month
)
SELECT
    cur.year,
    cur.month,
    ROUND(cur.revenue, 2) AS revenue,
    ROUND(prev.revenue, 2) AS prev_year_revenue,
    CASE
        WHEN prev.revenue IS NULL OR prev.revenue = 0 THEN NULL
        ELSE ROUND(100.0 * (cur.revenue - prev.revenue) / prev.revenue, 2)
    END AS yoy_growth_percent
FROM monthly_revenue cur
LEFT JOIN monthly_revenue prev
    ON prev.year = cur.year - 1 AND prev.month = cur.month
ORDER BY cur.year, cur.month;


-- 13. First/Last Value Analysis: first vs most recent purchased category per customer
WITH customer_category_orders AS (
    SELECT
        o.customer_id,
        o.order_date,
        p.category,
        FIRST_VALUE(p.category) OVER (
            PARTITION BY o.customer_id ORDER BY o.order_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS first_category,
        LAST_VALUE(p.category) OVER (
            PARTITION BY o.customer_id ORDER BY o.order_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS most_recent_category
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    JOIN products p ON p.product_id = oi.product_id
    WHERE o.customer_id IS NOT NULL
)
SELECT DISTINCT
    customer_id,
    first_category,
    most_recent_category,
    CASE WHEN first_category != most_recent_category THEN 'Yes' ELSE 'No' END AS category_shift
FROM customer_category_orders
ORDER BY customer_id;


-- 14. Cumulative Distribution: % of total revenue from top N% of customers
WITH customer_revenue AS (
    SELECT
        o.customer_id,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.customer_id IS NOT NULL
    GROUP BY o.customer_id
),
ranked AS (
    SELECT
        customer_id,
        revenue,
        SUM(revenue) OVER (ORDER BY revenue DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_revenue,
        SUM(revenue) OVER () AS total_revenue
    FROM customer_revenue
)
SELECT
    customer_id,
    ROUND(revenue, 2) AS revenue,
    ROUND(cumulative_revenue, 2) AS cumulative_revenue,
    ROUND(100.0 * cumulative_revenue / total_revenue, 2) AS cumulative_percent
FROM ranked
ORDER BY revenue DESC;


-- 15. Complex CTE: Cohort Analysis by registration month
--     month 0 = registration month; month 1/2/3 = calendar months after
WITH cohorts AS (
    SELECT
        customer_id,
        strftime('%Y-%m', registration_date) AS cohort_month
    FROM customers
),
customer_order_months AS (
    SELECT DISTINCT
        customer_id,
        strftime('%Y-%m', order_date) AS order_month
    FROM orders
    WHERE customer_id IS NOT NULL
),
cohort_activity AS (
    SELECT
        c.cohort_month,
        c.customer_id,
        (CAST(strftime('%Y', o.order_month || '-01') AS INTEGER) * 12 + CAST(strftime('%m', o.order_month || '-01') AS INTEGER))
        - (CAST(strftime('%Y', c.cohort_month || '-01') AS INTEGER) * 12 + CAST(strftime('%m', c.cohort_month || '-01') AS INTEGER))
        AS month_offset
    FROM cohorts c
    JOIN customer_order_months o ON o.customer_id = c.customer_id
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size
    FROM cohorts
    GROUP BY cohort_month
)
SELECT
    ca.cohort_month,
    cs.cohort_size,
    SUM(CASE WHEN ca.month_offset = 0 THEN 1 ELSE 0 END) AS month_0_active,
    SUM(CASE WHEN ca.month_offset = 1 THEN 1 ELSE 0 END) AS month_1_active,
    SUM(CASE WHEN ca.month_offset = 2 THEN 1 ELSE 0 END) AS month_2_active,
    SUM(CASE WHEN ca.month_offset = 3 THEN 1 ELSE 0 END) AS month_3_active,
    ROUND(100.0 * SUM(CASE WHEN ca.month_offset = 1 THEN 1 ELSE 0 END) / cs.cohort_size, 2) AS retention_month_1_pct,
    ROUND(100.0 * SUM(CASE WHEN ca.month_offset = 2 THEN 1 ELSE 0 END) / cs.cohort_size, 2) AS retention_month_2_pct,
    ROUND(100.0 * SUM(CASE WHEN ca.month_offset = 3 THEN 1 ELSE 0 END) / cs.cohort_size, 2) AS retention_month_3_pct
FROM cohort_activity ca
JOIN cohort_sizes cs ON cs.cohort_month = ca.cohort_month
WHERE ca.month_offset >= 0
GROUP BY ca.cohort_month, cs.cohort_size
ORDER BY ca.cohort_month;


-- 16. Self-Join with Window Function: customers whose 2nd order value exceeded
--     their 1st order value (illustrates self-referential comparison across
--     a customer's own order sequence using window functions)
WITH order_values AS (
    SELECT
        o.customer_id,
        o.order_id,
        o.order_date,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS order_value,
        ROW_NUMBER() OVER (PARTITION BY o.customer_id ORDER BY o.order_date) AS order_seq
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.customer_id IS NOT NULL
    GROUP BY o.customer_id, o.order_id, o.order_date
)
SELECT
    first_ord.customer_id,
    ROUND(first_ord.order_value, 2) AS first_order_value,
    ROUND(second_ord.order_value, 2) AS second_order_value,
    ROUND(second_ord.order_value - first_ord.order_value, 2) AS value_change
FROM order_values first_ord
JOIN order_values second_ord
    ON second_ord.customer_id = first_ord.customer_id
    AND second_ord.order_seq = first_ord.order_seq + 1
WHERE first_ord.order_seq = 1
  AND second_ord.order_value > first_ord.order_value
ORDER BY value_change DESC;
