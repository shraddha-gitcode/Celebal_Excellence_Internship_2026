# Data Cleaning Summary — Sales Dataset

**Input:** `sales_data.csv` (12 raw order records)
**Output:** `sales_data_cleaned.csv` (10 cleaned records)
**Notebook:** `Pandas_Data_Cleaning.ipynb` (full executed workflow with outputs)

## What was done

1. **Loaded** the CSV into a Pandas DataFrame.
2. **Explored** structure: 7 columns (`order_id`, `product`, `category`, `price`, `quantity`,
   `customer`, `order_date`), shape, dtypes, and summary stats.
3. **Missing values:**
   - `price` had 3 nulls → filled with the **per-category median** price (more accurate
     than one global median, since Electronics and Hardware price ranges differ).
   - `quantity` had 2 nulls → filled with **1** (a reasonable single-unit default).
4. **Filtering/selection** demonstrated: Electronics-only rows, quantity > 2, and a
   column subset (`order_id`, `product`, `price`, `quantity`).
5. **Duplicates:** found and removed **2 exact duplicate rows** (accidental double entries
   of order 1001 and order 1006).
6. **Derived column:** added `total_amount = price * quantity` for revenue analysis.
7. **Saved** the cleaned result to `sales_data_cleaned.csv`.

## Result

| | Rows | Nulls | Duplicates |
|---|---|---|---|
| Before | 12 | 5 | 2 |
| After | 10 | 0 | 0 |

The cleaned dataset is now duplicate-free, null-free, and includes `total_amount`,
ready for downstream analysis or loading into a BI tool / warehouse.
