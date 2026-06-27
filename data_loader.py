# ============================================================
# DATA LOADER — GasFeel Dashboard
# This file handles all data fetching from Google Sheets.
# Uses requests library to bypass Google's redirect block.
# ============================================================

import pandas as pd
import requests
from io import StringIO
import streamlit as st

# ============================================================
# GOOGLE SHEET URLs — Published to web as CSV
# To update data source, replace only these two URLs.
# ============================================================

# ============================================================
# GOOGLE SHEET URLs
# Loaded from Streamlit secrets — never hardcoded here.
# Locally: stored in .streamlit/secrets.toml
# On Streamlit Cloud: entered via the Secrets UI in settings.
# ============================================================
ORDERS_URL = st.secrets["ORDERS_URL"]
TARGETS_URL = st.secrets["TARGETS_URL"]

# ============================================================
# HELPER FUNCTION — FETCH CSV FROM URL
# Uses requests library with browser headers to avoid
# Google's HTTP 400 redirect block on direct pandas reads.
# ============================================================

def fetch_csv(url):
    # Mimic a browser request so Google allows the download
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    response = requests.get(url, headers=headers)

    # Raise an error if the request failed
    response.raise_for_status()

    # Convert the response text into a pandas DataFrame
    return pd.read_csv(StringIO(response.text))


# ============================================================
# LOAD ORDERS DATA
# Fetches and cleans the raw orders sheet.
# @st.cache_data caches for 10 minutes to keep dashboard fast.
# ============================================================

@st.cache_data(ttl=600)
def load_orders():

    # --------------------------------------------------------
    # FETCH RAW DATA FROM GOOGLE SHEETS
    # --------------------------------------------------------
    df = fetch_csv(ORDERS_URL)

    # --------------------------------------------------------
    # CLEAN COLUMN NAMES
    # Strips whitespace from headers to prevent key errors.
    # --------------------------------------------------------
    df.columns = df.columns.str.strip()
    # Drop empty unnamed columns caused by extra blank columns in Google Sheet
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    # --------------------------------------------------------
    # CONVERT DATE COLUMN TO DATETIME
    # Enables month, week, year filtering throughout dashboard.
    # --------------------------------------------------------
    df["Date of Order"] = pd.to_datetime(df["Date of Order"], errors="coerce")

    # --------------------------------------------------------
    # EXTRACT TIME COLUMNS FOR FILTERING
    # Creates Month, Month Name, Year, Week columns from date.
    # --------------------------------------------------------
    df["Month"] = df["Date of Order"].dt.month
    df["Month Name"] = df["Date of Order"].dt.strftime("%B")
    df["Year"] = df["Date of Order"].dt.year
    df["Week"] = df["Date of Order"].dt.isocalendar().week.astype(int)

    # --------------------------------------------------------
    # CLEAN NUMERIC COLUMNS
    # Removes commas from values like "1,300" and converts
    # all financial columns to proper numbers.
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
    # Protects all KPIs from bad/incomplete data entries.
    # --------------------------------------------------------
    df = df[df["Revenue (Total Customer Payment)"] > 0]

    # --------------------------------------------------------
    # CALCULATE PROFIT PER ORDER ROW
    # Profit = Revenue minus Cost of Goods minus Delivery Cost
    # --------------------------------------------------------
    df["Profit"] = (
        df["Revenue (Total Customer Payment)"]
        - df["COGS(naira)"]
        - df["Delivery Cost (how much we paid to the Rider)"]
    )

    # --------------------------------------------------------
    # CALCULATE DELIVERY DURATION IN MINUTES
    # Measures time from fulfillment start to completion.
    # --------------------------------------------------------
    df["Fulfillment Start Time"] = pd.to_datetime(
        df["Fulfillment Start Time"], format="%I:%M:%S %p", errors="coerce"
    )
    df["Order Completion Time"] = pd.to_datetime(
        df["Order Completion Time"], format="%I:%M:%S %p", errors="coerce"
    )
    df["Delivery Duration (mins)"] = (
        df["Order Completion Time"] - df["Fulfillment Start Time"]
    ).dt.total_seconds() / 60

    # --------------------------------------------------------
    # FLAG ON-TIME DELIVERIES
    # On-time = delivered within 25 minutes (GasFeel standard)
    # --------------------------------------------------------
    df["On Time"] = df["Delivery Duration (mins)"] <= 25

    # --------------------------------------------------------
    # FLAG FREE VS PAID DELIVERY
    # Free = customer paid zero delivery fee
    # --------------------------------------------------------
    df["Delivery Type"] = df[
        "Delivery Fee (Amount we Collected from the customer)"
    ].apply(lambda x: "Free" if x == 0 else "Paid")

    return df


# ============================================================
# LOAD TARGETS DATA
# Fetches the monthly/daily targets from second sheet tab.
# ============================================================

@st.cache_data(ttl=600)
def load_targets():

    # Fetch targets sheet
    df = fetch_csv(TARGETS_URL)

    # Clean column names
    df.columns = df.columns.str.strip()

    # Convert Period to datetime
    df["Period"] = pd.to_datetime(df["Period"], errors="coerce")

    # Clean numeric target columns
    target_columns = [
        "Target GMV",
        "Target Revenue",
        "Target Profit",
        "Target Orders",
        "Target Delivery Cost"
    ]

    for col in target_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False),
                errors="coerce"
            )

    return df