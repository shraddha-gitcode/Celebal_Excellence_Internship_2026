"""
Part 1: Data Generation
Generates 4 raw CSV files with realistic e-commerce data, seeded with
intentional data-quality issues so that Part 2 (cleaning) has real work to do.

Files produced (in ./data/raw/):
    customers.csv
    products.csv
    orders.csv
    order_items.csv

Design notes on referential integrity:
    - customers.csv and products.csv are generated FIRST, giving us a pool of
      valid customer_id / product_id values.
    - orders.csv is generated next, drawing customer_id from that pool (except
      for the rows we deliberately null out).
    - order_items.csv is generated LAST, and order_id values are drawn from
      the orders.csv we just created -- this is what keeps the two tables
      referentially consistent by default. We then deliberately inject a
      small number of "orphan" order_items rows (order_id not in orders) so
      that Part 2's check_referential_integrity() has something real to find.
"""
import csv
import os
import random
from datetime import datetime, timedelta

from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

RAW_DIR = os.path.join(os.path.dirname(__file__), "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

N_CUSTOMERS = 600
N_PRODUCTS = 550
N_ORDERS = 2500
# order_items will end up being roughly N_ORDERS * ~2.3 rows, comfortably >500

CATEGORIES = {
    "Electronics": ["Phones", "Laptops", "Accessories", "Cameras", "Audio"],
    "Clothing": ["Men", "Women", "Kids", "Footwear", "Winterwear"],
    "Home": ["Kitchen", "Furniture", "Decor", "Bedding", "Storage"],
    "Books": ["Fiction", "Non-Fiction", "Comics", "Academic", "Children"],
}

CUSTOMER_TYPES = ["REGULAR", "PREMIUM", "VIP"]
CUSTOMER_TYPE_WEIGHTS = [0.65, 0.25, 0.10]

ORDER_STATUSES = ["PLACED", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED"]
ORDER_STATUS_WEIGHTS = [0.10, 0.15, 0.55, 0.10, 0.10]


def messy_name_case(name: str) -> str:
    """Randomly mangle a name's casing/spacing to simulate dirty source data."""
    r = random.random()
    if r < 0.10:
        return f"  {name}  "          # extra spaces
    if r < 0.20:
        return name.upper()           # ALL CAPS
    if r < 0.30:
        return name.lower()           # all lower
    return name


def maybe_bad_email(email: str) -> str:
    """2% of emails become invalid (missing @ or missing domain)."""
    if random.random() < 0.02:
        choice = random.random()
        if choice < 0.5:
            return email.replace("@", "")          # missing @
        else:
            return email.split("@")[0] + "@"        # missing domain
    return email


def random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=seconds)


def format_order_date(dt: datetime) -> str:
    """~4% of orders get the wrong DD-MM-YYYY format instead of YYYY-MM-DD HH:MM:SS."""
    if random.random() < 0.04:
        return dt.strftime("%d-%m-%Y")
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# 1. customers.csv
# ---------------------------------------------------------------------------
def generate_customers():
    rows = []
    # Registration window overlaps the order-date window (2024-01 .. 2026-08)
    # so cohort analysis (month 0/1/2/3 retention) has real signal instead of
    # mostly-empty early cohorts.
    reg_start = datetime(2023, 9, 1)
    reg_end = datetime(2026, 5, 1)
    for i in range(1, N_CUSTOMERS + 1):
        first, last = fake.first_name(), fake.last_name()
        name = f"{first} {last}"
        email = f"{first}.{last}{random.randint(1,999)}@{fake.free_email_domain()}".lower()
        email = maybe_bad_email(email)
        reg_date = random_date(reg_start, reg_end).strftime("%Y-%m-%d")
        ctype = random.choices(CUSTOMER_TYPES, weights=CUSTOMER_TYPE_WEIGHTS)[0]
        rows.append({
            "customer_id": f"CUST{i:05d}",
            "customer_name": messy_name_case(name),
            "email": email,
            "registration_date": reg_date,
            "customer_type": ctype,
        })

    path = os.path.join(RAW_DIR, "customers.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"customers.csv -> {len(rows)} rows")
    return rows


# ---------------------------------------------------------------------------
# 2. products.csv
# ---------------------------------------------------------------------------
def generate_products():
    rows = []
    for i in range(1, N_PRODUCTS + 1):
        category = random.choice(list(CATEGORIES.keys()))
        subcategory = random.choice(CATEGORIES[category])
        base_name = f"{fake.word().capitalize()} {subcategory[:-1] if subcategory.endswith('s') else subcategory} {fake.word().capitalize()}"
        cost_price = round(random.uniform(5, 800), 2)
        rows.append({
            "product_id": f"PROD{i:05d}",
            "product_name": messy_name_case(base_name),
            "category": category,
            "subcategory": subcategory,
            "cost_price": cost_price,
        })

    path = os.path.join(RAW_DIR, "products.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"products.csv -> {len(rows)} rows")
    return rows


# ---------------------------------------------------------------------------
# 3. orders.csv
# ---------------------------------------------------------------------------
REGIONS = ["NORTH", "SOUTH", "EAST", "WEST", "CENTRAL"]


def generate_orders(customers):
    rows = []
    order_start = datetime(2024, 1, 1)
    order_end = datetime(2026, 8, 1)  # includes some "future" dates relative to a 2025 cutoff on purpose
    customer_ids = [c["customer_id"] for c in customers]

    for i in range(1, N_ORDERS + 1):
        # 5% missing customer_id
        if random.random() < 0.05:
            cust_id = ""  # empty -> treated as NULL
        else:
            cust_id = random.choice(customer_ids)

        odt = random_date(order_start, order_end)
        status = random.choices(ORDER_STATUSES, weights=ORDER_STATUS_WEIGHTS)[0]

        rows.append({
            "order_id": f"ORD{i:06d}",
            "customer_id": cust_id,
            "order_date": format_order_date(odt),
            "status": status,
            "region_code": random.choice(REGIONS),
        })

    path = os.path.join(RAW_DIR, "orders.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"orders.csv -> {len(rows)} rows")
    return rows


# ---------------------------------------------------------------------------
# 4. order_items.csv
# ---------------------------------------------------------------------------
def generate_order_items(orders, products):
    rows = []
    item_id = 1
    order_ids = [o["order_id"] for o in orders]
    product_pool = products

    for order in orders:
        n_items = random.randint(1, 4)
        chosen_products = random.sample(product_pool, k=min(n_items, len(product_pool)))
        for prod in chosen_products:
            qty = random.randint(1, 5)
            # 3% of rows: negative quantity (return)
            if random.random() < 0.03:
                qty = -abs(qty)

            unit_price = round(prod["cost_price"] * random.uniform(1.2, 2.5), 2)
            discount = random.choice([0, 0, 0, 5, 10, 15, 20, 25, 30])
            # occasionally inject an invalid discount > 100 to test validation
            if random.random() < 0.005:
                discount = random.choice([110, 150, 200])

            rows.append({
                "order_item_id": f"ITEM{item_id:07d}",
                "order_id": order["order_id"],
                "product_id": prod["product_id"],
                "product_name": prod["product_name"],
                "quantity": qty,
                "unit_price": unit_price,
                "discount_percent": discount,
            })
            item_id += 1

    # Inject orphan rows: order_items referencing an order_id that does not exist
    n_orphans = max(5, int(0.005 * len(rows)))
    for _ in range(n_orphans):
        prod = random.choice(product_pool)
        rows.append({
            "order_item_id": f"ITEM{item_id:07d}",
            "order_id": f"ORD{random.randint(900000, 999999)}",  # not a real order_id
            "product_id": prod["product_id"],
            "product_name": prod["product_name"],
            "quantity": random.randint(1, 3),
            "unit_price": round(prod["cost_price"] * 1.5, 2),
            "discount_percent": 0,
        })
        item_id += 1

    random.shuffle(rows)

    path = os.path.join(RAW_DIR, "order_items.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"order_items.csv -> {len(rows)} rows (incl. {n_orphans} orphan rows for integrity testing)")
    return rows


def main():
    print("Generating raw e-commerce data with intentional data-quality issues...\n")
    customers = generate_customers()
    products = generate_products()
    orders = generate_orders(customers)
    generate_order_items(orders, products)
    print(f"\nDone. Raw files written to: {RAW_DIR}")


if __name__ == "__main__":
    main()
