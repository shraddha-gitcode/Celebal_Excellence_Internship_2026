"""
Part 4: Python + SQL Integration -- Command-line Reporting Tool

Usage (interactive):
    python3 report_tool.py

Usage (non-interactive, for scripting/automation):
    python3 report_tool.py --type daily   --start 2024-06-01 --end 2024-06-07
    python3 report_tool.py --type weekly  --start 2024-06-01 --end 2024-06-30
    python3 report_tool.py --type monthly --start 2024-01-01 --end 2024-12-31

Only the standard library (sqlite3, argparse, datetime) is used -- no
external dependencies.
"""
import argparse
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "ecommerce.db"
REVENUE_EXPR = "oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)"


def parse_date(s: str) -> datetime:
    return datetime.strptime(s.strip(), "%Y-%m-%d")


def get_period_summary(conn, start: str, end: str) -> dict:
    """start/end are 'YYYY-MM-DD' strings, end is inclusive (whole day)."""
    cur = conn.cursor()
    end_exclusive = (parse_date(end) + timedelta(days=1)).strftime("%Y-%m-%d")

    cur.execute(f"""
        SELECT
            COUNT(DISTINCT o.order_id)      AS total_orders,
            COALESCE(SUM({REVENUE_EXPR}), 0) AS total_revenue,
            COUNT(DISTINCT o.customer_id)    AS unique_customers
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.order_id
        WHERE o.order_date >= ? AND o.order_date < ?
    """, (start, end_exclusive))
    total_orders, total_revenue, unique_customers = cur.fetchone()

    cur.execute(f"""
        SELECT p.product_name, SUM({REVENUE_EXPR}) AS rev
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.order_id
        JOIN products p ON p.product_id = oi.product_id
        WHERE o.order_date >= ? AND o.order_date < ?
        GROUP BY p.product_id, p.product_name
        ORDER BY rev DESC
        LIMIT 3
    """, (start, end_exclusive))
    top_products = cur.fetchall()

    return {
        "start": start,
        "end": end,
        "total_orders": total_orders or 0,
        "total_revenue": round(total_revenue or 0, 2),
        "unique_customers": unique_customers or 0,
        "top_products": top_products,
    }


def previous_period(start: str, end: str) -> tuple[str, str]:
    """Returns the immediately preceding period of the same length."""
    start_dt, end_dt = parse_date(start), parse_date(end)
    length = (end_dt - start_dt) + timedelta(days=1)
    prev_end = start_dt - timedelta(days=1)
    prev_start = prev_end - length + timedelta(days=1)
    return prev_start.strftime("%Y-%m-%d"), prev_end.strftime("%Y-%m-%d")


def pct_change(current: float, previous: float):
    if not previous:
        return None
    return round(100.0 * (current - previous) / previous, 2)


def print_report(report_type: str, start: str, end: str):
    conn = sqlite3.connect(DB_PATH)
    current = get_period_summary(conn, start, end)
    prev_start, prev_end = previous_period(start, end)
    previous = get_period_summary(conn, prev_start, prev_end)
    conn.close()

    print()
    print("=" * 60)
    print(f"{report_type.upper()} REPORT: {start} to {end}")
    print("=" * 60)
    print(f"Total Orders      : {current['total_orders']}")
    print(f"Total Revenue     : ${current['total_revenue']:,.2f}")
    print(f"Unique Customers  : {current['unique_customers']}")

    print("\nTop 3 Products:")
    if current["top_products"]:
        for i, (name, rev) in enumerate(current["top_products"], 1):
            print(f"  {i}. {name:<35} ${rev:,.2f}")
    else:
        print("  (no orders in this period)")

    print(f"\nComparison to previous period ({prev_start} to {prev_end}):")
    orders_chg = pct_change(current["total_orders"], previous["total_orders"])
    revenue_chg = pct_change(current["total_revenue"], previous["total_revenue"])
    customers_chg = pct_change(current["unique_customers"], previous["unique_customers"])

    def fmt_chg(v):
        if v is None:
            return "N/A (no data in previous period)"
        sign = "+" if v >= 0 else ""
        return f"{sign}{v}%"

    print(f"  Orders     : {previous['total_orders']} -> {current['total_orders']}  ({fmt_chg(orders_chg)})")
    print(f"  Revenue    : ${previous['total_revenue']:,.2f} -> ${current['total_revenue']:,.2f}  ({fmt_chg(revenue_chg)})")
    print(f"  Customers  : {previous['unique_customers']} -> {current['unique_customers']}  ({fmt_chg(customers_chg)})")
    print("=" * 60)


def prompt_for_inputs():
    print("E-Commerce Order Analytics -- Report Generator")
    print("-" * 50)
    while True:
        report_type = input("Report type (daily/weekly/monthly): ").strip().lower()
        if report_type in ("daily", "weekly", "monthly"):
            break
        print("Please enter one of: daily, weekly, monthly")

    while True:
        start = input("Start date (YYYY-MM-DD): ").strip()
        end = input("End date   (YYYY-MM-DD): ").strip()
        try:
            if parse_date(start) > parse_date(end):
                print("Start date must be on or before end date. Try again.")
                continue
            break
        except ValueError:
            print("Dates must be in YYYY-MM-DD format. Try again.")

    return report_type, start, end


def main():
    parser = argparse.ArgumentParser(description="E-Commerce order analytics reporting tool")
    parser.add_argument("--type", choices=["daily", "weekly", "monthly"], help="Report type")
    parser.add_argument("--start", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", help="End date YYYY-MM-DD")
    args = parser.parse_args()

    if args.type and args.start and args.end:
        report_type, start, end = args.type, args.start, args.end
    else:
        report_type, start, end = prompt_for_inputs()

    try:
        print_report(report_type, start, end)
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}. Did you run load_to_sqlite.py first?")


if __name__ == "__main__":
    main()
