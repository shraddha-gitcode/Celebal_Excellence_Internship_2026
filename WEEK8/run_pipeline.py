"""
Runs the full pipeline end-to-end in order:
    1. generate_data.py    -> data/raw/*.csv
    2. clean_data.py       -> data/clean/*.csv + data_quality_report.txt
    3. load_to_sqlite.py   -> ecommerce.db
    4. test_edge_cases.py  -> sanity-checks the cleaning logic

After this, use queries.sql (any SQLite client) and report_tool.py (CLI)
against ecommerce.db.
"""
import subprocess
import sys

STEPS = [
    ("Generating raw data", ["python3", "generate_data.py"]),
    ("Cleaning data", ["python3", "clean_data.py"]),
    ("Loading into SQLite", ["python3", "load_to_sqlite.py"]),
    ("Running edge case tests", ["python3", "test_edge_cases.py"]),
]

for label, cmd in STEPS:
    print(f"\n{'='*60}\n{label}\n{'='*60}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\nStep failed: {label}")
        sys.exit(result.returncode)

print("\nAll steps complete. Try:")
print("  python3 report_tool.py --type monthly --start 2024-06-01 --end 2024-06-30")
print("  sqlite3 ecommerce.db < queries.sql   (or run queries.sql from any SQLite client)")
