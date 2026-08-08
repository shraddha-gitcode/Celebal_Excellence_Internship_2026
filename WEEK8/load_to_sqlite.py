"""
Loads the cleaned CSVs (data/clean/*.csv) into a SQLite database
(ecommerce.db) so Part 3's SQL queries and Part 4's CLI tool can run
against real, integrity-checked data.
"""
import os
import sqlite3
import pandas as pd

BASE_DIR = os.path.dirname(__file__)
CLEAN_DIR = os.path.join(BASE_DIR, "data", "clean")
DB_PATH = os.path.join(BASE_DIR, "ecommerce.db")


def load():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)

    customers = pd.read_csv(os.path.join(CLEAN_DIR, "customers_clean.csv"))
    products = pd.read_csv(os.path.join(CLEAN_DIR, "products_clean.csv"))
    orders = pd.read_csv(os.path.join(CLEAN_DIR, "orders_clean.csv"))
    order_items = pd.read_csv(os.path.join(CLEAN_DIR, "order_items_clean.csv"))

    # normalize booleans / types coming out of pandas CSV round-trip
    for col in ("customer_id_missing", "is_future_dated"):
        if col in orders.columns:
            orders[col] = orders[col].astype(str).str.lower().isin(["true", "1"])
    for col in ("is_return", "discount_percent_flagged_invalid"):
        if col in order_items.columns:
            order_items[col] = order_items[col].astype(str).str.lower().isin(["true", "1"])
    if "email_valid" in customers.columns:
        customers["email_valid"] = customers["email_valid"].astype(str).str.lower().isin(["true", "1"])

    customers.to_sql("customers", conn, if_exists="replace", index=False)
    products.to_sql("products", conn, if_exists="replace", index=False)
    orders.to_sql("orders", conn, if_exists="replace", index=False)
    order_items.to_sql("order_items", conn, if_exists="replace", index=False)

    cur = conn.cursor()
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_items_order ON order_items(order_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_items_product ON order_items(product_id)")
    conn.commit()

    print(f"Loaded into {DB_PATH}:")
    for table in ("customers", "products", "orders", "order_items"):
        n = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {n} rows")

    conn.close()


if __name__ == "__main__":
    load()
