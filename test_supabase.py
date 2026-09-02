# ============================================================
# TEST SUPABASE CONNECTION
# Run this to confirm Supabase is connecting and returning data.
# Delete this file after testing is complete.
# ============================================================

from supabase import create_client

S
print("Connecting to Supabase...")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Test 1 — Count orders
print("\n=== TEST 1: Orders table ===")
result = supabase.table("orders").select("id", count="exact").execute()
print(f"Total orders in database: {result.count}")

# Test 2 — Sample 3 orders
print("\n=== TEST 2: Sample orders ===")
result = supabase.table("orders").select(
    "id,created_at,product,status,zone,grand_total"
).limit(3).execute()
for row in result.data:
    print(row)

# Test 3 — Count customers
print("\n=== TEST 3: Customers table ===")
result = supabase.table("customers").select("whatsapp_number", count="exact").execute()
print(f"Total customers: {result.count}")

# Test 4 — Count completed orders
print("\n=== TEST 4: Completed orders only ===")
result = supabase.table("orders").select(
    "id", count="exact"
).eq("status", "completed").execute()
print(f"Completed orders: {result.count}")

# Test 5 — ops_targets
print("\n=== TEST 5: Targets table ===")
result = supabase.table("ops_targets").select("*").limit(3).execute()
print(f"Targets rows found: {len(result.data)}")
for row in result.data:
    print(row)

# Test 6 — Interactions and Agents
print("\n=== TEST 6: Interactions and Agents ===")
result = supabase.table("interactions").select("id", count="exact").execute()
print(f"Total interactions: {result.count}")

result = supabase.table("profiles").select("id", count="exact").execute()
print(f"Total agents: {result.count}")

# Test 7 — Sample interaction to see structure
print("\n=== TEST 7: Sample interaction ===")
result = supabase.table("interactions").select("*").limit(2).execute()
for row in result.data:
    print(row)

# Test 8 — Petrol orders per customer per month from Supabase
print("\n=== TEST 8: Petrol orders count ===")
result = supabase.table("orders").select(
    "id,product,customer_whatsapp,created_at"
).eq("status", "closed").execute()
print(f"Total closed orders: {len(result.data)}")
petrol = [r for r in result.data if r.get("product") == "petrol"]
print(f"Petrol orders: {len(petrol)}")
gas = [r for r in result.data if r.get("product") == "gas"]
print(f"Gas orders: {len(gas)}")

# ============================================================
# TEST 9 — Find delivery time outliers in Supabase
# ============================================================
print("\n=== TEST 9: Delivery Time Analysis ===")

result = supabase.table("orders").select(
    "id,created_at,fulfillment_start,completion_time,"
    "measured_delivery_time,zone,product,status"
).eq("status", "closed").execute()

import pandas as pd

df = pd.DataFrame(result.data)
df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
df["fulfillment_start"] = pd.to_datetime(df["fulfillment_start"], utc=True, format="ISO8601")
df["completion_time"] = pd.to_datetime(df["completion_time"], utc=True, format="ISO8601")


# Calculate delivery duration in minutes
df["delivery_mins"] = (
    df["completion_time"] - df["fulfillment_start"]
).dt.total_seconds() / 60

df["total_mins"] = (
    df["completion_time"] - df["created_at"]
).dt.total_seconds() / 60

print(f"\nTotal closed orders: {len(df)}")
print(f"\nDelivery duration stats (mins):")
print(df["delivery_mins"].describe())

print(f"\nTotal duration stats (mins):")
print(df["total_mins"].describe())

print(f"\nOrders with delivery > 60 mins:")
outliers = df[df["delivery_mins"] > 60].sort_values("delivery_mins", ascending=False)
print(outliers[["id","created_at","fulfillment_start","completion_time","delivery_mins","total_mins","zone","product"]].to_string())

print(f"\nOrders with NULL fulfillment_start or completion_time:")
nulls = df[df["fulfillment_start"].isna() | df["completion_time"].isna()]
print(f"Count: {len(nulls)}")


print("\n=== TEST 10: Check Google Sheets delivery time issue ===")
import pandas as pd
import requests
from io import StringIO

ORDERS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS3CDt_ulHB-4JN80DKixskyHZhE_caf75oKICt-dirQNmBb3gH9WDNDVrkXY2Y0ja862OV1DXv3y72/pub?gid=1183636741&single=true&output=csv"

headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(ORDERS_URL, headers=headers)
df = pd.read_csv(StringIO(response.text))
df.columns = df.columns.str.strip()
df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

# Parse time columns
df["Order Time Parsed"] = pd.to_datetime(
    df["Order Time"].astype(str).str.strip(),
    format="%I:%M:%S %p", errors="coerce"
)
df["Fulfillment Start Parsed"] = pd.to_datetime(
    df["Fulfillment Start Time"].astype(str).str.strip(),
    format="%I:%M:%S %p", errors="coerce"
)
df["Completion Parsed"] = pd.to_datetime(
    df["Order Completion Time"].astype(str).str.strip(),
    format="%I:%M:%S %p", errors="coerce"
)

# Calculate delivery duration
df["delivery_mins"] = (
    df["Completion Parsed"] - df["Fulfillment Start Parsed"]
).dt.total_seconds() / 60

# Fix midnight crossover
df.loc[df["delivery_mins"] < 0, "delivery_mins"] = df.loc[
    df["delivery_mins"] < 0, "delivery_mins"
] + 1440

print(f"Delivery duration stats (mins):")
print(df["delivery_mins"].describe())

print(f"\nOrders with delivery > 90 mins:")
outliers = df[df["delivery_mins"] > 90].sort_values("delivery_mins", ascending=False)
print(f"Count: {len(outliers)}")
print(outliers[["Order ID", "Order Time", "Fulfillment Start Time", "Order Completion Time", "delivery_mins"]].head(20).to_string())

print("\n=== TEST 11: Check financial columns in Supabase orders ===")

result = supabase.table("orders").select(
    "id,grand_total,rider_payout,delivery_fee,"
    "cost_price,margin,vat,deposit_used"
).eq("status", "closed").limit(10).execute()

print("Sample orders financial data:")
for row in result.data:
    print(row)

print("\n=== TEST 12: Check order_items financial columns ===")
result = supabase.table("order_items").select("*").limit(5).execute()
print("Sample order_items:")
for row in result.data:
    print(row)
print("\n=== ALL TESTS COMPLETE ===")


