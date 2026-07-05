# Superstore Sales Analysis — Query Results & Insights

Dataset: `Sample - Superstore.csv` — 9,994 order lines loaded into `superstore_raw`, then split into:

| Table | Row count |
|---|---|
| `customers` | 793 |
| `products` | 1,862 |
| `orders` | 9,994 |

Total company sales across all orders: **$2,297,200.86**

---

## Step 2: Required Queries — Results

### 2.1 Orders with sales above the average (Subquery)
Average order sales ≈ **$229.86**. **2,360 of 9,994 orders (23.6%)** are above it. Top 10:

| Order ID | Customer ID | Sales |
|---|---|---|
| CA-2014-145317 | SM-20320 | 22,638.48 |
| CA-2016-118689 | TC-20980 | 17,499.95 |
| CA-2017-140151 | RB-19360 | 13,999.96 |
| CA-2017-127180 | TA-21385 | 11,199.97 |
| CA-2017-166709 | HL-15040 | 10,499.97 |
| CA-2016-117121 | AB-10105 | 9,892.74 |
| CA-2014-116904 | SC-20095 | 9,449.95 |
| US-2016-107440 | BS-11365 | 9,099.93 |
| CA-2016-158841 | SE-20110 | 8,749.95 |
| CA-2016-143714 | CC-12370 | 8,399.98 |

### 2.2 Highest-sales single order per customer (Subquery)
Top 10 of 793 customers:

| Customer | Order ID | Sales |
|---|---|---|
| Sean Miller | CA-2014-145317 | 22,638.48 |
| Tamara Chand | CA-2016-118689 | 17,499.95 |
| Raymond Buch | CA-2017-140151 | 13,999.96 |
| Tom Ashbrook | CA-2017-127180 | 11,199.97 |
| Hunter Lopez | CA-2017-166709 | 10,499.97 |
| Adrian Barton | CA-2016-117121 | 9,892.74 |
| Sanjit Chand | CA-2014-116904 | 9,449.95 |
| Bill Shonely | US-2016-107440 | 9,099.93 |
| Sanjit Engle | CA-2016-158841 | 8,749.95 |
| Christopher Conant | CA-2016-143714 | 8,399.98 |

### 2.3 Total sales per customer (CTE)
Top 10 of 793:

| Customer | Total Sales |
|---|---|
| Sean Miller | 25,043.05 |
| Tamara Chand | 19,052.22 |
| Raymond Buch | 15,117.34 |
| Tom Ashbrook | 14,595.62 |
| Adrian Barton | 14,473.57 |
| Ken Lonsdale | 14,175.23 |
| Sanjit Chand | 14,142.33 |
| Hunter Lopez | 12,873.30 |
| Sanjit Engle | 12,209.44 |
| Christopher Conant | 12,129.07 |

### 2.4 Customers above average total sales (CTE + Subquery)
Average total sales per customer = **$2,896.85**. **294 of 793 customers (37.1%)** are above it (same ranking as 2.3, truncated at $2,896.85).

### 2.5 / Step 3 — Rank all customers (Window Function, `RANK()`)
Same ordering as 2.3, with a `sales_rank` column added (ties share a rank, next rank skips accordingly). Ranks 1–15:

| Rank | Customer | Total Sales |
|---|---|---|
| 1 | Sean Miller | 25,043.05 |
| 2 | Tamara Chand | 19,052.22 |
| 3 | Raymond Buch | 15,117.34 |
| 4 | Tom Ashbrook | 14,595.62 |
| 5 | Adrian Barton | 14,473.57 |
| 6 | Ken Lonsdale | 14,175.23 |
| 7 | Sanjit Chand | 14,142.33 |
| 8 | Hunter Lopez | 12,873.30 |
| 9 | Sanjit Engle | 12,209.44 |
| 10 | Christopher Conant | 12,129.07 |
| 11 | Todd Sumrall | 11,891.75 |
| 12 | Greg Tran | 11,820.12 |
| 13 | Becky Martin | 11,789.63 |
| 14 | Seth Vernon | 11,470.95 |
| 15 | Caroline Jumper | 11,164.97 |

### 2.6 Row number per order within customer (`ROW_NUMBER() PARTITION BY`)
Example for customer `AA-10315` (Alex Avila), ordered by order date:

| Order ID | Order Date | Sales | Seq # |
|---|---|---|---|
| CA-2015-121391 | 10/4/2015 | 26.96 | 1 |
| CA-2016-103982 | 3/3/2016 | 3,930.07 | 2 |
| CA-2016-103982 | 3/3/2016 | 2.30 | 3 |
| CA-2016-103982 | 3/3/2016 | 431.98 | 4 |
| CA-2016-103982 | 3/3/2016 | 41.72 | 5 |
| CA-2014-128055 | 3/31/2014 | 673.57 | 6 |
| CA-2014-128055 | 3/31/2014 | 52.98 | 7 |
| CA-2017-147039 | 6/29/2017 | 362.94 | 8 |
| CA-2017-147039 | 6/29/2017 | 11.54 | 9 |
| CA-2014-138100 | 9/15/2014 | 14.94 | 10 |

This assigns a sequence number per *order line* within a customer (multiple products in one order get consecutive numbers). The full result set covers all 9,994 rows.

### 2.7 Top 3 customers by total sales (`DENSE_RANK()`)

| Customer | Total Sales | Rank |
|---|---|---|
| Sean Miller | 25,043.05 | 1 |
| Tamara Chand | 19,052.22 | 2 |
| Raymond Buch | 15,117.34 | 3 |

---

## Step 3: Final Combined Query (JOIN + CTE + Window Function)
Customer Name / Total Sales / Rank — identical result set to 2.5 above, produced via one JOIN + one CTE + `RANK()`. Full 793-row output ranks every customer from highest to lowest total sales.

---

## Mini Project: Customer Sales Insights

### 1) Top 5 customers
| Customer | Total Sales |
|---|---|
| Sean Miller | 25,043.05 |
| Tamara Chand | 19,052.22 |
| Raymond Buch | 15,117.34 |
| Tom Ashbrook | 14,595.62 |
| Adrian Barton | 14,473.57 |

### 2) Bottom 5 customers
| Customer | Total Sales |
|---|---|
| Thais Sissman | 4.83 |
| Lela Donovan | 5.30 |
| Carl Jackson | 16.52 |
| Mitch Gastineau | 16.74 |
| Roy Skaria | 22.33 |

### 3) Customers who made only one order
**12 customers** placed exactly one order (one distinct `order_id`, though some of those orders contain multiple product lines):
Anemone Ratner, Anthony O'Donnell, Carl Jackson, Jenna Caffey, Jocasta Rupert, Lela Donovan, Mitch Gastineau, Patricia Hirasaki, Ricardo Emerson, Roland Murray, Susan MacKendrick, Theresa Coyne.

Note the overlap with the bottom-5 list (Carl Jackson, Lela Donovan, Mitch Gastineau) — single-order customers are naturally at risk of low total sales.

### 4) Customers with above-average sales
**294 of 793 customers (37.1%)** have total sales above the $2,896.85 average — same list as query 2.4/2.5, cut off at that threshold.

### 5) Highest order value per customer
Top 10 (same as 2.2's ranking by customer):

| Customer | Highest Order Value |
|---|---|
| Sean Miller | 22,638.48 |
| Tamara Chand | 17,499.95 |
| Raymond Buch | 13,999.96 |
| Tom Ashbrook | 11,199.97 |
| Hunter Lopez | 10,499.97 |
| Adrian Barton | 9,892.74 |
| Sanjit Chand | 9,449.95 |
| Bill Shonely | 9,099.93 |
| Sanjit Engle | 8,749.95 |
| Christopher Conant | 8,399.98 |

---

## Brief Insights

- **Revenue is concentrated at the top.** The 5 highest-spending customers contribute **$88,281.80**, only **3.8%** of total company sales ($2,297,200.86) — spending is not extremely concentrated among a handful of accounts, but there's still a meaningful "power user" tier worth account-managing directly (Sean Miller, Tamara Chand, Raymond Buch, Tom Ashbrook, Adrian Barton).
- **Sean Miller is an outlier.** His #1 ranking is driven almost entirely by one $22,638.48 order — the single largest order in the whole dataset (a bulk copier purchase). Without that one order, his total sales would be much closer to the pack. This is a useful reminder that "top customer by total sales" and "consistently high-value customer" aren't always the same thing — worth checking order frequency alongside total spend.
- **A meaningful minority of customers (37.1%) drive above-average revenue,** roughly matching a Pareto-style pattern common in retail: a bit more than a third of customers pull the average up, while the majority sit below it.
- **12 customers have only ever ordered once.** Several of these are also in the bottom-5 by total sales, which makes sense — a single small order caps lifetime value. This group is a natural target for a re-engagement or win-back campaign, since acquiring them already cost something and a second order is usually cheaper to generate than a new customer.
- **The bottom 5 customers all have total sales under $25** — likely single small accessory purchases (e.g., binders, labels). These accounts contribute negligible revenue individually but in aggregate represent the long tail typical of a broad retail customer base.

---

## Files
- `superstore_sales_analysis.sql` — full SQL script (schema, load, all 7 required queries, Step 3 combined query, mini-project queries)
- `superstore_query_results.md` — this file (results + insights)
