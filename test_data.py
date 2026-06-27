# ============================================================
# TEST FILE — Confirms data loads correctly from Google Sheets
# Run with: python test_data.py
# Delete this file after testing is complete.
# ============================================================

from data_loader import fetch_csv, ORDERS_URL, TARGETS_URL
import pandas as pd

print("Testing Orders data...")
orders = fetch_csv(ORDERS_URL)
orders.columns = orders.columns.str.strip()
print(f"Total rows: {len(orders)}")
print(f"Columns: {list(orders.columns)}")
print(f"\nSample row:")
print(orders.head(2).to_string())

print("\n\nTesting Targets data...")
targets = fetch_csv(TARGETS_URL)
targets.columns = targets.columns.str.strip()
print(f"Total rows: {len(targets)}")
print(f"Columns: {list(targets.columns)}")