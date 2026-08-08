"""
Part 5: Edge Case Handling

Each test function documents:
  - What the edge case is
  - What SHOULD happen (the expected/designed behavior)
  - An assertion proving the pipeline actually behaves that way

Run with:  python3 test_edge_cases.py
(uses only the standard library's unittest-style asserts -- no pytest needed,
though it will also work fine under `pytest test_edge_cases.py`)
"""
import pandas as pd
from clean_data import clean_order_items, check_referential_integrity, clean_orders


def test_order_item_with_nonexistent_order_id():
    """
    Edge case 1: order_items has an order_id not present in orders.
    Expected behavior: check_referential_integrity() flags it as an orphan,
    and clean_order_items() removes it from the cleaned dataset rather than
    silently letting it corrupt joins/revenue totals downstream.
    """
    orders = pd.DataFrame({"order_id": ["ORD1", "ORD2"]})
    order_items = pd.DataFrame({
        "order_item_id": ["I1", "I2"],
        "order_id": ["ORD1", "ORD_GHOST"],   # ORD_GHOST does not exist
        "product_id": ["P1", "P2"],
        "product_name": ["Widget", "Gadget"],
        "quantity": [2, 1],
        "unit_price": [10.0, 20.0],
        "discount_percent": [0, 0],
    })

    orphans = check_referential_integrity(orders, order_items)
    assert len(orphans) == 1
    assert orphans.iloc[0]["order_id"] == "ORD_GHOST"

    cleaned, stats = clean_order_items(order_items, valid_order_ids=set(orders["order_id"]))
    assert stats["order_items_orphans_removed"] == 1
    assert "ORD_GHOST" not in cleaned["order_id"].values
    assert len(cleaned) == 1
    print("PASS: orphan order_items (order_id not in orders) is detected and removed")


def test_discount_percent_over_100():
    """
    Edge case 2: discount_percent > 100 (invalid -- can't discount more than
    the full price).
    Expected behavior: the row is flagged via
    discount_percent_flagged_invalid=True, and the value used for downstream
    revenue math is clipped to the valid [0, 100] range rather than producing
    a negative "revenue" figure.
    """
    order_items = pd.DataFrame({
        "order_item_id": ["I1"],
        "order_id": ["ORD1"],
        "product_id": ["P1"],
        "product_name": ["Widget"],
        "quantity": [2],
        "unit_price": [10.0],
        "discount_percent": [150],   # invalid
    })
    cleaned, stats = clean_order_items(order_items, valid_order_ids={"ORD1"})
    assert stats["order_items_invalid_discount"] == 1
    assert bool(cleaned.iloc[0]["discount_percent_flagged_invalid"]) is True
    assert cleaned.iloc[0]["discount_percent"] == 100  # clipped, not left at 150
    print("PASS: discount_percent > 100 is flagged and clipped to 100 for revenue math")


def test_quantity_zero():
    """
    Edge case 3: quantity == 0 (contributes no revenue and isn't a return).
    Expected behavior: the row is kept (it's not corrupt data, just a
    no-op line item) but counted in order_items_zero_quantity so analysts
    can see how many such rows exist; it is NOT marked as a return.
    """
    order_items = pd.DataFrame({
        "order_item_id": ["I1"],
        "order_id": ["ORD1"],
        "product_id": ["P1"],
        "product_name": ["Widget"],
        "quantity": [0],
        "unit_price": [10.0],
        "discount_percent": [0],
    })
    cleaned, stats = clean_order_items(order_items, valid_order_ids={"ORD1"})
    assert stats["order_items_zero_quantity"] == 1
    assert len(cleaned) == 1  # kept, not dropped
    assert bool(cleaned.iloc[0]["is_return"]) is False
    print("PASS: quantity == 0 is kept and counted, and not misclassified as a return")


def test_order_date_in_future():
    """
    Edge case 4: order_date is in the future relative to now.
    Expected behavior: clean_orders() does NOT reject/drop the row (it might
    be legitimate test data, a scheduled/pre-order, or a timezone quirk) but
    flags it via is_future_dated=True and reports the count in stats, so
    downstream consumers can decide whether to exclude it.
    """
    far_future = (pd.Timestamp.now() + pd.Timedelta(days=3650)).strftime("%Y-%m-%d %H:%M:%S")
    orders = pd.DataFrame({
        "order_id": ["ORD1"],
        "customer_id": ["CUST1"],
        "order_date": [far_future],
        "status": ["PLACED"],
        "region_code": ["NORTH"],
    })
    cleaned, stats = clean_orders(orders)
    assert stats["orders_future_dated"] == 1
    assert bool(cleaned.iloc[0]["is_future_dated"]) is True
    assert len(cleaned) == 1  # not dropped
    print("PASS: future-dated orders are flagged (is_future_dated=True) rather than silently dropped")


def test_negative_quantity_is_flagged_as_return():
    """
    Bonus edge case: negative quantity should be recognized as a RETURN,
    distinct from the quantity==0 no-op case above.
    """
    order_items = pd.DataFrame({
        "order_item_id": ["I1"],
        "order_id": ["ORD1"],
        "product_id": ["P1"],
        "product_name": ["Widget"],
        "quantity": [-3],
        "unit_price": [10.0],
        "discount_percent": [0],
    })
    cleaned, stats = clean_order_items(order_items, valid_order_ids={"ORD1"})
    assert stats["order_items_returns"] == 1
    assert bool(cleaned.iloc[0]["is_return"]) is True
    print("PASS: negative quantity is correctly flagged as a return (is_return=True)")


def test_missing_customer_id_kept_but_flagged():
    """
    Bonus edge case: orders.csv rows with NULL/blank customer_id should be
    kept (they can represent legitimate guest checkouts) but clearly
    flagged, rather than being dropped and silently losing revenue.
    """
    orders = pd.DataFrame({
        "order_id": ["ORD1", "ORD2"],
        "customer_id": ["", "CUST1"],
        "order_date": ["2024-01-01 10:00:00", "2024-01-02 10:00:00"],
        "status": ["PLACED", "PLACED"],
        "region_code": ["NORTH", "SOUTH"],
    })
    cleaned, stats = clean_orders(orders)
    assert stats["orders_missing_customer_id"] == 1
    assert len(cleaned) == 2
    assert bool(cleaned.iloc[0]["customer_id_missing"]) is True
    print("PASS: missing customer_id is kept and flagged, not silently dropped")


def run_all():
    tests = [
        test_order_item_with_nonexistent_order_id,
        test_discount_percent_over_100,
        test_quantity_zero,
        test_order_date_in_future,
        test_negative_quantity_is_flagged_as_return,
        test_missing_customer_id_kept_but_flagged,
    ]
    print("Running edge case tests...\n")
    failures = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failures += 1
            print(f"FAIL: {t.__name__} -> {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} tests passed")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    run_all()
