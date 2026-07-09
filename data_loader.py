# ============================================================
# DATA LOADER — GasFeel Dashboard
# This file handles all data fetching and cleaning from Google Sheets.
# Uses requests library to bypass Google's redirect block.
# All cleaning happens here so every tab receives clean data.
# ============================================================

import pandas as pd
import requests
from io import StringIO
import streamlit as st


# ============================================================
# GOOGLE SHEET URLs — Loaded from Streamlit secrets
# Locally stored in .streamlit/secrets.toml
# On Streamlit Cloud: entered via Secrets UI in settings
# ============================================================
ORDERS_URL = st.secrets["ORDERS_URL"]
TARGETS_URL = st.secrets["TARGETS_URL"]


# ============================================================
# HELPER — FETCH CSV FROM URL
# Uses browser headers to avoid Google's HTTP 400 block
# ============================================================
def fetch_csv(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return pd.read_csv(StringIO(response.text))


# ============================================================
# LOAD ORDERS DATA
# Fetches, cleans, and enriches the raw orders sheet.
# Cached for 10 minutes to keep dashboard fast.
# ============================================================
@st.cache_data(ttl=600)
def load_orders():

    # --------------------------------------------------------
    # FETCH RAW DATA
    # --------------------------------------------------------
    df = fetch_csv(ORDERS_URL)

    # --------------------------------------------------------
    # DROP EMPTY UNNAMED COLUMNS
    # Google Sheets exports extra blank columns — remove them.
    # --------------------------------------------------------
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

    # --------------------------------------------------------
    # CLEAN ALL COLUMN NAMES
    # Strip whitespace from headers to prevent key errors.
    # --------------------------------------------------------
    df.columns = df.columns.str.strip()

    # --------------------------------------------------------
    # CLEAN TEXT COLUMNS — Strip whitespace and proper case
    # Fixes duplicates like "olamide", "Olamide ", "OLAMIDE"
    # all becoming "Olamide" so customer counts are accurate.
    # --------------------------------------------------------
    text_columns = [
        "Customer Name",
        "Rider Name",
        "Order Area/Location",
        "Station",
        "Order Type",
        "Day of the Week",
        "Comments",
        "Referral Code"
    ]
    for col in text_columns:
        if col in df.columns:
            # Strip leading/trailing spaces then apply title case
            df[col] = df[col].astype(str).str.strip().str.title()
            # Replace "Nan" strings that come from empty cells
            df[col] = df[col].replace("Nan", None)

    # --------------------------------------------------------
    # SPECIFIC NAME STANDARDISATION
    # Some rider names have known spelling variants.
    # Map all variants to one consistent name.
    # --------------------------------------------------------
    rider_name_map = {
        "Abdulahi": "Abdullahi",
        "Abdulai": "Abdullahi",
        "Abdulahi ": "Abdullahi",
        "Mr. Bola": "Mr Bola",
        "Mrbola": "Mr Bola",
        "The Hero ": "The Hero",
        "Tumise ": "Tumise",
    }
    if "Rider Name" in df.columns:
        df["Rider Name"] = df["Rider Name"].replace(rider_name_map)

    # --------------------------------------------------------
    # CONVERT DATE COLUMN TO DATETIME
    # Enables month, week, year filtering throughout dashboard.
    # --------------------------------------------------------
    df["Date of Order"] = pd.to_datetime(df["Date of Order"], errors="coerce")
    # Drop rows where date could not be parsed — prevents NA errors in filters
    df = df.dropna(subset=["Date of Order"])

    # --------------------------------------------------------
    # EXTRACT TIME COLUMNS FOR FILTERING
    # --------------------------------------------------------
    df["Month"] = df["Date of Order"].dt.month
    df["Month Name"] = df["Date of Order"].dt.strftime("%B")
    df["Year"] = df["Date of Order"].dt.year
    # Use nullable integer to handle NaT dates without crashing
    df["Week"] = df["Date of Order"].dt.isocalendar().week.astype("Int64")
    # --------------------------------------------------------
    # CLEAN NUMERIC COLUMNS
    # Removes commas from values like "1,300" and converts
    # all financial and quantity columns to proper numbers.
    # --------------------------------------------------------
    numeric_columns = [
        "Cost Price (Per kg/liter)",
        "Selling Price (Per kg/Liter)",
        "Litre/Kg Sold",
        "Delivery Cost (how much we paid to the Rider)",
        "Delivery Fee (Amount we Collected from the customer)",
        "Revenue (Total Customer Payment)",
        "COGS(naira)"
    ]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False),
                errors="coerce"
            )

    # --------------------------------------------------------
    # REMOVE ZERO OR NULL REVENUE ROWS
    # Protects all KPIs from bad or incomplete data entries.
    # --------------------------------------------------------
    df = df[df["Revenue (Total Customer Payment)"] > 0]

    # --------------------------------------------------------
    # CORRECT REVENUE MODEL
    # Per GasFeel's DAX model:
    #   GMV     = Total Customer Payment (what customer paid)
    #   Revenue = GMV - COGS (what GasFeel keeps after product cost)
    #   Profit  = Revenue - Delivery Cost (true profitability)
    # --------------------------------------------------------
    df["GMV"] = df["Revenue (Total Customer Payment)"]
    df["Revenue"] = df["GMV"] - df["COGS(naira)"]
    df["Profit"] = df["Revenue"] - df["Delivery Cost (how much we paid to the Rider)"]

    # --------------------------------------------------------
    # DELIVERY TIME CALCULATIONS
    # Three separate time metrics as per GasFeel's requirements:
    #   1. Order to Completion — full customer journey time
    #   2. Order to Fulfillment Start — initiation/response time
    #   3. Fulfillment Start to Completion — actual delivery time
    # --------------------------------------------------------
    df["Order Time Parsed"] = pd.to_datetime(
        df["Order Time"], format="%I:%M:%S %p", errors="coerce"
    )
    df["Fulfillment Start Parsed"] = pd.to_datetime(
        df["Fulfillment Start Time"], format="%I:%M:%S %p", errors="coerce"
    )
    df["Completion Parsed"] = pd.to_datetime(
        df["Order Completion Time"], format="%I:%M:%S %p", errors="coerce"
    )

    # Full journey: Order placed to Order completed
    df["Total Duration (mins)"] = (
        df["Completion Parsed"] - df["Order Time Parsed"]
    ).dt.total_seconds() / 60

    # Initiation time: Order placed to Fulfillment started
    df["Initiation Duration (mins)"] = (
        df["Fulfillment Start Parsed"] - df["Order Time Parsed"]
    ).dt.total_seconds() / 60

    # Delivery time: Fulfillment started to Completed
    df["Delivery Duration (mins)"] = (
        df["Completion Parsed"] - df["Fulfillment Start Parsed"]
    ).dt.total_seconds() / 60

    # Remove negative durations — data entry errors
    df.loc[df["Total Duration (mins)"] < 0, "Total Duration (mins)"] = None
    df.loc[df["Initiation Duration (mins)"] < 0, "Initiation Duration (mins)"] = None
    df.loc[df["Delivery Duration (mins)"] < 0, "Delivery Duration (mins)"] = None

    # --------------------------------------------------------
    # ON-TIME FLAG
    # On-time = full journey (order to completion) <= 10 mins
    # --------------------------------------------------------
    df["On Time"] = df["Total Duration (mins)"] <= 10

    # --------------------------------------------------------
    # FREE VS PAID DELIVERY FLAG
    # Free = customer paid zero delivery fee
    # --------------------------------------------------------
    df["Delivery Type"] = df[
        "Delivery Fee (Amount we Collected from the customer)"
    ].apply(lambda x: "Free" if x == 0 else "Paid")

    # --------------------------------------------------------
    # ORDER HOUR — for hourly pattern chart
    # --------------------------------------------------------
    df["Order Hour"] = df["Order Time Parsed"].dt.hour

    return df


# ============================================================
# LOAD TARGETS DATA
# Fetches the targets sheet and cleans numeric columns.
# ============================================================
@st.cache_data(ttl=600)
def load_targets():
    df = fetch_csv(TARGETS_URL)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df.columns = df.columns.str.strip()
    df["Period"] = pd.to_datetime(df["Period"], errors="coerce")

    target_columns = [
        "Target GMV", "Target Revenue",
        "Target Profit", "Target Orders", "Target Delivery Cost"
    ]
    for col in target_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False),
                errors="coerce"
            )
    return df