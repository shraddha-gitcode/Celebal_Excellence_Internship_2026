## SHRADDHA SANJAY WAKCHAURE - SCOE

---

## Package Contents

```
ShopEase_SQL_Week2/
├── README.md                          ← This file
├── queries/
│   └── ShopEase_Complete_SQL.sql      ← Full SQL script (all sections)
└── screenshots/                       ← MySQL Workbench output screenshots
    ├── Q1_all_customers.png
    ├── Q2_name_city.png
    ├── Q3_unique_categories.png
    ├── Q7_delivered_orders.png
    ├── Q8_electronics_gt2000.png
    ├── Q9_maharashtra_2024.png
    ├── Q10_aug10_25_not_cancelled.png
    ├── Q13_total_orders.png
    ├── Q14_delivered_revenue.png
    ├── Q15_avg_price_category.png
    ├── Q16_revenue_by_status.png
    ├── Q17_max_min_price.png
    ├── Q18_having_avg_gt2000.png
    ├── Q19_inner_join.png
    ├── Q20_left_join.png
    ├── Q21_3table_join.png
    ├── Q24_price_tiers.png
    ├── Q25_delivered_vs_not.png
    ├── Q27_transaction.png
    ├── BONUS1_top3_customers.png
    └── BONUS2_data_quality.png
```

---

## How to Run

1. Open **MySQL Workbench** and connect to your local server.
2. Create a new schema: `CREATE SCHEMA shopease;` → select it as active.
3. Open `queries/ShopEase_Complete_SQL.sql` via **File → Open SQL Script**.
4. Run the full script with **Ctrl+Shift+Enter**, or execute section by section
   using **Ctrl+Enter** (run selected query only).

> Compatible with **MySQL 8.x**, **PostgreSQL 14+**, and **SQLite 3.x**.
> Minor syntax adjustments may be needed for PostgreSQL
> (e.g. `BOOLEAN` → `BOOL`, `CURRENT_DATE` stays the same, `strftime` → `TO_CHAR`).

---

## Database Schema

```
customers ──(1:N)──▶ orders ──(1:N)──▶ order_items ◀──(1:N)── products
```

| Table        | Rows | Primary Key | Key Constraints             |
|--------------|------|-------------|-----------------------------|
| customers    | 8    | customer_id | email UNIQUE NOT NULL        |
| products     | 8    | product_id  | unit_price > 0               |
| orders       | 10   | order_id    | status IN (4 values), FK     |
| order_items  | 15   | item_id     | quantity > 0, discount 0-100 |

---

## Section Summary

### Section A — SQL Basics (Q1–Q6)
| Q  | Topic                       | Key Result |
|----|-----------------------------|------------|
| Q1 | SELECT * from customers     | 8 rows returned |
| Q2 | Select specific columns     | first_name, last_name, city |
| Q3 | DISTINCT categories         | Electronics, Clothing, Home |
| Q4 | Primary Keys analysis       | Conceptual explanation |
| Q5 | UNIQUE + NOT NULL on email  | Constraint violation demo |
| Q6 | CHECK constraint on price   | Rejects unit_price = -50 |

### Section B — Filtering & Optimization (Q7–Q12)
| Q   | Topic                         | Key Result |
|-----|-------------------------------|------------|
| Q7  | WHERE status = 'Delivered'    | 6 orders |
| Q8  | Electronics AND price > 2000  | 2 products (Smart Watch, BT Speaker) |
| Q9  | Maharashtra + 2024 join date  | 2 customers (both premium) |
| Q10 | Date range, NOT Cancelled     | 5 orders, ₹17,693 value |
| Q11 | Index on order_date explained | Enables Index Range Scan |
| Q12 | SARGable query rewrite        | YEAR() breaks index; use range instead |

### Section C — Aggregation (Q13–Q18)
| Q   | Topic                    | Key Result |
|-----|--------------------------|------------|
| Q13 | COUNT(*) orders          | 10 total orders |
| Q14 | SUM Delivered revenue    | ₹17,191 |
| Q15 | AVG price per category   | Clothing ₹2699, Electronics ₹2224, Home ₹949 |
| Q16 | GROUP BY status + ORDER  | Delivered leads at ₹17,191 |
| Q17 | MAX / MIN per category   | Nike Shoes ₹4599 (top), Cushion Covers ₹599 (cheapest) |
| Q18 | HAVING avg > ₹2000       | Clothing & Electronics qualify |

### Section D — Joins & Relationships (Q19–Q23)
| Q   | Topic                      | Key Result |
|-----|----------------------------|------------|
| Q19 | INNER JOIN orders+customers| 10 rows, names matched |
| Q20 | LEFT JOIN (all customers)  | All 8 customers shown; repeat buyers visible |
| Q21 | 3-table JOIN               | 15 line items with product names |
| Q22 | LEFT vs RIGHT vs FULL OUTER| Conceptual explanation with examples |
| Q23 | FK relationships + violation| customer_id=999 raises FK error |

### Section E — Advanced Concepts (Q24–Q27)
| Q   | Topic                    | Key Result |
|-----|--------------------------|------------|
| Q24 | CASE price tiers         | 3 Budget, 3 Mid-Range, 2 Premium |
| Q25 | CASE inside SUM          | 6 Delivered, 4 Not Delivered |
| Q26 | ACID properties          | Full explanation with bank-transfer example |
| Q27 | BEGIN…COMMIT transaction | 1 order + 2 items + 2 stock updates atomically |

### Bonus Queries
| Query  | Topic                | Key Result |
|--------|----------------------|------------|
| BONUS1 | Top 3 customers      | Rohan Gupta ₹8397, Aarav Sharma ₹7997, Karan Mehta ₹6098 |
| BONUS2 | Data quality audit   | All 4 tables: 0 NULL values found |

---

## Key Business Insights

| Metric | Value |
|--------|-------|
| Total orders | 10 |
| Delivered (fulfilled) | 6 (60%) |
| Revenue — Delivered | ₹17,191 |
| Revenue — Shipped (in transit) | ₹13,596 |
| Revenue — at risk (Pending + Cancelled) | ₹4,298 |
| Repeat purchase customers | Aarav Sharma (×2), Rohan Gupta (×2) |
| Top-spending customer | Rohan Gupta — ₹8,397 |
| Highest-value single order | #1003 — ₹7,498 |
| Best average price category | Clothing (₹2,699 avg) |
| Data quality issues found | None — 0 NULLs across all tables |

---

## ACID in One Line (Q26 Summary)

| Letter | Property    | Guarantee |
|--------|-------------|-----------|
| A | Atomicity   | All steps commit or all roll back — never half-done |
| C | Consistency | Constraints respected; DB stays in a valid state |
| I | Isolation   | Concurrent transactions can't see each other's mid-state |
| D | Durability  | Committed data survives crashes (WAL/disk flush) |

---

## Index Strategy Used

| Index Name               | Column          | Benefits |
|--------------------------|-----------------|----------|
| idx_customers_city       | customers.city  | Fast city-based lookup |
| idx_customers_state      | customers.state | Fast state-based filter (Q9) |
| idx_products_category    | products.category | Fast category filter (Q8, Q15, Q18) |
| idx_orders_date          | orders.order_date | Index Range Scan for date filters (Q10, Q11) |
| idx_orders_status        | orders.status   | Fast status filter (Q7, Q14, Q16) |

> **SARGability Note (Q12):** `WHERE YEAR(join_date) = 2024` forces a full table
> scan because the function wraps the column. Rewrite as:
> `WHERE join_date >= '2024-01-01' AND join_date < '2025-01-01'`
> to allow the B-tree index to be used.

---


