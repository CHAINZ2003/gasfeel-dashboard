import pandas as pd
import requests
from io import StringIO

# Your Google Sheets CSV URL
ORDERS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS3CDt_ulHB-4JN80DKixskyHZhE_caf75oKICt-dirQNmBb3gH9WDNDVrkXY2Y0ja862OV1DXv3y72/pub?gid=1183636741&single=true&output=csv"

print("Fetching and processing Google Sheets data...")

# Fetch data
headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(ORDERS_URL, headers=headers)
df = pd.read_csv(StringIO(response.text))

# Clean column names
df.columns = df.columns.str.strip()
df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

# Convert dates and apply the August 1 cutoff
df["Date of Order"] = pd.to_datetime(df["Date of Order"], errors="coerce")
df = df.dropna(subset=["Date of Order"])
df = df[df["Date of Order"] < pd.Timestamp("2026-08-01")]

# Clean numeric columns (remove commas and convert to float)
numeric_cols = [
    "Revenue (Total Customer Payment)", 
    "COGS(naira)", 
    "Delivery Cost (how much we paid to the Rider)", 
    "Delivery Fee (Amount we Collected from the customer)"
]

for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(",", "", regex=False), 
            errors="coerce"
        ).fillna(0)

# Keep valid orders (including the 0-revenue fix we just did)
df = df[df["Revenue (Total Customer Payment)"] >= 0]

# Calculate financial metrics (matching your Python model)
total_orders = len(df)
gmv = df["Revenue (Total Customer Payment)"].sum()
total_cogs = df["COGS(naira)"].sum()
revenue = gmv - total_cogs
total_delivery_cost_paid = df["Delivery Cost (how much we paid to the Rider)"].sum()
profit = revenue - total_delivery_cost_paid

total_delivery_fee_collected = df["Delivery Fee (Amount we Collected from the customer)"].sum()
delivery_profit = total_delivery_fee_collected - total_delivery_cost_paid

# Calculate Margins
revenue_margin = (revenue / gmv * 100) if gmv > 0 else 0
profit_margin = (profit / revenue * 100) if revenue > 0 else 0

# Print Results
print("\n" + "="*50)
print("GOOGLE SHEETS KPIs (Jan 1, 2026 - Jul 31, 2026)")
print("="*50)
print(f"Total Orders:                  {total_orders:,}")
print(f"GMV (Total Payments):          ₦{gmv:,.2f}")
print(f"Total COGS:                    ₦{total_cogs:,.2f}")
print(f"Revenue (GMV - COGS):          ₦{revenue:,.2f}")
print(f"Profit (Revenue - Del Cost):   ₦{profit:,.2f}")
print("-" * 50)
print(f"Delivery Fees Collected:       ₦{total_delivery_fee_collected:,.2f}")
print(f"Delivery Costs Paid to Riders: ₦{total_delivery_cost_paid:,.2f}")
print(f"Delivery Profit:               ₦{delivery_profit:,.2f}")
print("-" * 50)
print(f"Revenue Margin:                {revenue_margin:.2f}%")
print(f"Profit Margin:                 {profit_margin:.2f}%")
print("="*50)
