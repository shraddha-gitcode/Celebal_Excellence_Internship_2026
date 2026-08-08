"""
Part 2: Data Cleaning (pandas)

Implements:
    clean_orders()
    clean_products()
    validate_emails()
    check_referential_integrity()

Running this script end-to-end:
    - reads data/raw/*.csv
    - cleans orders + products
    - validates emails on customers
    - checks order_items -> orders referential integrity
    - writes cleaned CSVs to data/clean/
    - writes a human-readable issues report to data/clean/data_quality_report.txt
"""
import os
import re
import pandas as pd

BASE_DIR = os.path.dirname(__file__)
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
CLEAN_DIR = os.path.join(BASE_DIR, "data", "clean")
os.makedirs(CLEAN_DIR, exist_ok=True)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------------------
def clean_orders(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Fixes:
      - order_date: normalizes both 'YYYY-MM-DD HH:MM:SS' and the wrong
        'DD-MM-YYYY' format into a single proper datetime column.
      - customer_id: blank/NULL-like values become pandas NA; rows are kept
        (an order can legitimately be missing a customer, e.g. guest
        checkout) but are flagged in a new `customer_id_missing` column so
        downstream SQL/reporting can decide how to treat them.
    Returns (cleaned_df, stats_dict)
    """
    df = df.copy()
    stats = {}

    # --- customer_id ---
    df["customer_id"] = df["customer_id"].replace(
        r"^\s*$", pd.NA, regex=True
    )
    df["customer_id"] = df["customer_id"].where(df["customer_id"].notna(), pd.NA)
    stats["orders_missing_customer_id"] = int(df["customer_id"].isna().sum())
    df["customer_id_missing"] = df["customer_id"].isna()

    # --- order_date: handle two known formats ---
    def parse_date(value):
        if pd.isna(value):
            return pd.NaT
        value = str(value).strip()
        # Try the canonical format first
        for fmt in ("%Y-%m-%d %H:%M:%S", "%d-%m-%Y"):
            try:
                return pd.to_datetime(value, format=fmt)
            except ValueError:
                continue
        # Fall back to pandas' flexible parser as a last resort
        return pd.to_datetime(value, errors="coerce")

    wrong_format_mask = df["order_date"].astype(str).str.match(r"^\d{2}-\d{2}-\d{4}$")
    stats["orders_wrong_date_format"] = int(wrong_format_mask.sum())

    df["order_date"] = df["order_date"].apply(parse_date)
    stats["orders_unparseable_dates"] = int(df["order_date"].isna().sum())

    # --- future dates flag (edge case surfaced, not silently dropped) ---
    now = pd.Timestamp.now()
    df["is_future_dated"] = df["order_date"] > now
    stats["orders_future_dated"] = int(df["is_future_dated"].sum())

    # --- status normalization ---
    df["status"] = df["status"].astype(str).str.strip().str.upper()
    valid_statuses = {"PLACED", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED"}
    stats["orders_invalid_status"] = int((~df["status"].isin(valid_statuses)).sum())

    return df, stats


# ---------------------------------------------------------------------------
def clean_products(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Fixes:
      - product_name: trims whitespace and applies Title Case
      - category / subcategory: trims whitespace, Title Case
      - cost_price: coerces to numeric, flags negative/zero/non-numeric prices
    """
    df = df.copy()
    stats = {}

    before_names = df["product_name"].copy()
    df["product_name"] = df["product_name"].astype(str).str.strip().str.title()
    stats["products_name_normalized"] = int((before_names.astype(str) != df["product_name"]).sum())

    df["category"] = df["category"].astype(str).str.strip().str.title()
    df["subcategory"] = df["subcategory"].astype(str).str.strip().str.title()

    df["cost_price"] = pd.to_numeric(df["cost_price"], errors="coerce")
    stats["products_invalid_cost_price"] = int(df["cost_price"].isna().sum())
    stats["products_nonpositive_cost_price"] = int((df["cost_price"] <= 0).sum())

    # de-duplicate exact duplicate products created by whitespace/case noise
    before = len(df)
    df = df.drop_duplicates(subset=["product_id"])
    stats["products_duplicate_ids_dropped"] = before - len(df)

    return df, stats


# ---------------------------------------------------------------------------
def validate_emails(customers_df: pd.DataFrame) -> list:
    """Returns a list of customer_ids whose email fails a basic RFC-lite check
    (must contain exactly one @ with a non-empty local part and a domain that
    contains a dot)."""
    invalid_ids = []
    for _, row in customers_df.iterrows():
        email = str(row.get("email", "")).strip()
        if not EMAIL_RE.match(email):
            invalid_ids.append(row["customer_id"])
    return invalid_ids


# ---------------------------------------------------------------------------
def check_referential_integrity(orders_df: pd.DataFrame, order_items_df: pd.DataFrame) -> pd.DataFrame:
    """Returns the subset of order_items rows whose order_id does not exist
    in orders_df. These are 'orphan' rows that should be excluded (or
    investigated) before loading into the SQL layer."""
    valid_order_ids = set(orders_df["order_id"])
    orphan_mask = ~order_items_df["order_id"].isin(valid_order_ids)
    return order_items_df[orphan_mask].copy()


# ---------------------------------------------------------------------------
def clean_order_items(df: pd.DataFrame, valid_order_ids: set) -> tuple[pd.DataFrame, dict]:
    """
    Additional item-level cleaning:
      - drops orphan rows (order_id not in orders)
      - flags negative quantity as `is_return`
      - clamps/flags discount_percent > 100 (invalid) instead of silently
        using it in revenue math
      - flags quantity == 0 rows (a genuine edge case: no revenue impact,
        kept but flagged rather than dropped)
    """
    df = df.copy()
    stats = {}

    before = len(df)
    df = df[df["order_id"].isin(valid_order_ids)].copy()
    stats["order_items_orphans_removed"] = before - len(df)

    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["is_return"] = df["quantity"] < 0
    stats["order_items_returns"] = int(df["is_return"].sum())
    stats["order_items_zero_quantity"] = int((df["quantity"] == 0).sum())

    df["discount_percent"] = pd.to_numeric(df["discount_percent"], errors="coerce")
    invalid_discount_mask = (df["discount_percent"] > 100) | (df["discount_percent"] < 0)
    stats["order_items_invalid_discount"] = int(invalid_discount_mask.sum())
    # Flag rather than silently clip, so analysts can see what happened;
    # for downstream revenue math we clip to a valid 0-100 range.
    df["discount_percent_flagged_invalid"] = invalid_discount_mask
    df["discount_percent"] = df["discount_percent"].clip(lower=0, upper=100)

    df["product_name"] = df["product_name"].astype(str).str.strip().str.title()

    return df, stats


# ---------------------------------------------------------------------------
def main():
    print("Loading raw data...")
    orders_raw = pd.read_csv(os.path.join(RAW_DIR, "orders.csv"), dtype=str)
    products_raw = pd.read_csv(os.path.join(RAW_DIR, "products.csv"), dtype=str)
    customers_raw = pd.read_csv(os.path.join(RAW_DIR, "customers.csv"), dtype=str)
    order_items_raw = pd.read_csv(os.path.join(RAW_DIR, "order_items.csv"), dtype=str)

    report_lines = ["E-COMMERCE DATA QUALITY REPORT", "=" * 40, ""]

    # --- Orders ---
    orders_clean, order_stats = clean_orders(orders_raw)
    report_lines.append("[orders.csv]")
    for k, v in order_stats.items():
        report_lines.append(f"  {k}: {v}")

    # --- Products ---
    products_clean, product_stats = clean_products(products_raw)
    report_lines.append("\n[products.csv]")
    for k, v in product_stats.items():
        report_lines.append(f"  {k}: {v}")

    # --- Customers / email validation ---
    invalid_email_ids = validate_emails(customers_raw)
    report_lines.append("\n[customers.csv]")
    report_lines.append(f"  customers_with_invalid_email: {len(invalid_email_ids)}")
    customers_clean = customers_raw.copy()
    customers_clean["customer_name"] = customers_clean["customer_name"].astype(str).str.strip().str.title()
    customers_clean["email_valid"] = ~customers_clean["customer_id"].isin(invalid_email_ids)

    # --- Referential integrity + order_items cleaning ---
    orphans = check_referential_integrity(orders_raw, order_items_raw)
    report_lines.append("\n[order_items.csv <-> orders.csv]")
    report_lines.append(f"  orphan_order_items (order_id not found in orders): {len(orphans)}")

    valid_order_ids = set(orders_raw["order_id"])
    order_items_clean, item_stats = clean_order_items(order_items_raw, valid_order_ids)
    for k, v in item_stats.items():
        report_lines.append(f"  {k}: {v}")

    # --- Write cleaned files ---
    orders_clean.to_csv(os.path.join(CLEAN_DIR, "orders_clean.csv"), index=False)
    products_clean.to_csv(os.path.join(CLEAN_DIR, "products_clean.csv"), index=False)
    customers_clean.to_csv(os.path.join(CLEAN_DIR, "customers_clean.csv"), index=False)
    order_items_clean.to_csv(os.path.join(CLEAN_DIR, "order_items_clean.csv"), index=False)
    orphans.to_csv(os.path.join(CLEAN_DIR, "order_items_orphans.csv"), index=False)

    report_lines.append("\n" + "=" * 40)
    report_lines.append(f"Cleaned files written to: {CLEAN_DIR}")

    report_path = os.path.join(CLEAN_DIR, "data_quality_report.txt")
    with open(report_path, "w") as f:
        f.write("\n".join(report_lines))

    print("\n".join(report_lines))
    print(f"\nReport saved to {report_path}")


if __name__ == "__main__":
    main()
