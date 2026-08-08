# E-Commerce Order Analytics System

A complete local Python + SQL pipeline: generate messy e-commerce data,
clean and validate it, load it into SQLite, run 16 analytical SQL queries
(joins, window functions, CTEs, cohort analysis), and query it through a
small CLI reporting tool. No paid services or external APIs required.

## Requirements

```
pip install pandas faker --break-system-packages
```
(`sqlite3` is part of the Python standard library.)

## Quick start

```bash
python3 run_pipeline.py
```

This runs, in order: `generate_data.py` → `clean_data.py` →
`load_to_sqlite.py` → `test_edge_cases.py`.

Then explore:

```bash
# Run all 16 analytical queries (any SQLite client works)
sqlite3 ecommerce.db < queries.sql

# CLI reporting tool
python3 report_tool.py --type monthly --start 2024-06-01 --end 2024-06-30
python3 report_tool.py            # interactive mode, prompts for input
```

## Project layout

```
generate_data.py       Part 1 - creates data/raw/{orders,order_items,products,customers}.csv
                        with intentional issues (missing customer_id, bad date
                        formats, messy casing, invalid emails, negative
                        quantities, orphan order_items, etc.)

clean_data.py           Part 2 - clean_orders(), clean_products(),
                        validate_emails(), check_referential_integrity(),
                        clean_order_items(). Writes data/clean/*.csv plus
                        data/clean/data_quality_report.txt.

load_to_sqlite.py       Loads the cleaned CSVs into ecommerce.db (SQLite).

queries.sql             Part 3 - all 16 required SQL queries: 3 basic,
                        3 intermediate, 10 advanced (window functions,
                        multi-level CTEs, NTILE, YoY, cohort analysis, etc.)

report_tool.py          Part 4 - stdlib-only CLI: daily/weekly/monthly report
                        with total orders/revenue/customers, top 3 products,
                        and % change vs. the previous period of equal length.

test_edge_cases.py      Part 5 - tests for: order_items referencing a
                        nonexistent order_id, discount_percent > 100,
                        quantity == 0, and future-dated orders (plus two
                        bonus cases: negative quantity as a return, and
                        missing customer_id handling).

run_pipeline.py          Convenience script that runs steps 1-4 in order.
```

## Design decisions worth knowing about

- **Referential integrity**: `order_items.csv` is generated *from* the
  `orders.csv` that was just created, which is what keeps `order_id` valid
  by construction. A small number of orphan rows (~0.5%) are then
  deliberately injected so `check_referential_integrity()` has real orphans
  to find — they're removed during cleaning and also written out separately
  to `data/clean/order_items_orphans.csv` for inspection.
- **Nothing is silently dropped except true orphans.** Missing
  `customer_id`, future-dated orders, and out-of-range discounts are all
  **flagged with a boolean column** (`customer_id_missing`,
  `is_future_dated`, `discount_percent_flagged_invalid`) rather than
  deleted, so downstream SQL/reporting can decide how to treat them. Invalid
  discounts are clipped to `[0, 100]` for revenue math specifically, since
  an unclipped value would otherwise produce nonsensical (or negative)
  "revenue".
- **Revenue formula** used consistently across all queries and the CLI tool:
  `quantity * unit_price * (1 - discount_percent / 100.0)`.
- **Ranking ties** (query 8) use `RANK()`, not `ROW_NUMBER()` or
  `DENSE_RANK()`, because the spec says "products with the same revenue
  should have the same rank" — `RANK()` satisfies that while still reserving
  the rank positions ties consume (e.g. two products tied for #1 → both
  rank 1, next product is rank 3).
