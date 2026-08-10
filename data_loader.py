# ============================================================
# DATA LOADER — GasFeel Dashboard
# DUAL SOURCE with clean date cutoff:
# Google Sheets → Jan 2026 to Jul 31 2026 (historical)
# Supabase → Aug 1 2026 onwards (live app data)
# No overlap. No duplicates. Clean merge.
# ============================================================

import pandas as pd
import streamlit as st
import requests
from io import StringIO
from supabase import create_client


# ============================================================
# CUTOFF DATE
# Everything before this = Google Sheets
# Everything from this date = Supabase
# ============================================================
SUPABASE_CUTOFF = pd.Timestamp("2026-08-01")


# ============================================================
# GOOGLE SHEETS URLs
# ============================================================
ORDERS_URL  = st.secrets["ORDERS_URL"]
TARGETS_URL = st.secrets["TARGETS_URL"]


# ============================================================
# SUPABASE CLIENT
# ============================================================
@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )


# ============================================================
# HELPER — FETCH CSV FROM GOOGLE SHEETS
# ============================================================
def fetch_csv(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return pd.read_csv(StringIO(response.text))


# ============================================================
# HELPER — FETCH ALL ROWS FROM SUPABASE TABLE
# Loops pages since API returns max 1000 rows at once.
# ============================================================
def fetch_all_rows(table, select="*", eq_filter=None):
    supabase  = get_supabase()
    all_rows  = []
    page_size = 1000
    offset    = 0

    while True:
        query = supabase.table(table).select(select)
        if eq_filter:
            for col, val in eq_filter.items():
                query = query.eq(col, val)
        result = query.range(offset, offset + page_size - 1).execute()
        rows   = result.data
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < page_size:
            break
        offset += page_size

    return pd.DataFrame(all_rows) if all_rows else pd.DataFrame()


# ============================================================
# HELPER — CLEAN AND ENRICH DATAFRAME
# Applies cleaning, date parsing, and calculated columns
# to any dataframe regardless of source.
# ============================================================
def clean_and_enrich(df):

    # Clean column names
    df.columns = df.columns.str.strip()

    # Drop unnamed columns (Google Sheets artifact)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

    # --------------------------------------------------------
    # CONVERT DATE OF ORDER
    # Both sources use "Date of Order" column after renaming.
    # --------------------------------------------------------
    df["Date of Order"] = pd.to_datetime(df["Date of Order"], errors="coerce")
    df = df.dropna(subset=["Date of Order"])

    # Extract time period columns for filters
    df["Month"]      = df["Date of Order"].dt.month
    df["Month Name"] = df["Date of Order"].dt.strftime("%B")
    df["Year"]       = df["Date of Order"].dt.year
    df["Week"]       = df["Date of Order"].dt.isocalendar().week.astype("Int64")

    # Clean text columns — proper case, strip whitespace
    text_cols = [
        "Customer Name", "Rider Name",
        "Order Area/Location", "Station", "Order Type"
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()
            df[col] = df[col].replace("Nan", None)

    # Clean numeric columns — remove commas
    numeric_cols = [
        "Cost Price (Per kg/liter)",
        "Selling Price (Per kg/Liter)",
        "Litre/Kg Sold",
        "Delivery Cost (how much we paid to the Rider)",
        "Delivery Fee (Amount we Collected from the customer)",
        "Revenue (Total Customer Payment)",
        "COGS(naira)"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False),
                errors="coerce"
            )

    # Remove zero or null revenue rows
    df = df[df["Revenue (Total Customer Payment)"] > 0]

    # --------------------------------------------------------
    # REVENUE MODEL
    # GMV     = Total Customer Payment
    # Revenue = GMV - COGS
    # Profit  = Revenue - Delivery Cost
    # --------------------------------------------------------
    df["GMV"] = df["Revenue (Total Customer Payment)"]

    if "Revenue" not in df.columns or df["Revenue"].isna().all():
        df["Revenue"] = df["GMV"] - df["COGS(naira)"].fillna(0)

    if "Profit" not in df.columns or df["Profit"].isna().all():
        df["Profit"] = (
            df["Revenue"] -
            df["Delivery Cost (how much we paid to the Rider)"].fillna(0)
        )

    # --------------------------------------------------------
    # DELIVERY TIME CALCULATIONS
    # Midnight crossover fix: add 1440 mins if result negative.
    # --------------------------------------------------------
    def parse_time(col):
        if col in df.columns:
            return pd.to_datetime(
                df[col].astype(str).str.strip(),
                format="%I:%M:%S %p", errors="coerce"
            )
        return pd.Series([pd.NaT] * len(df), index=df.index)

    order_time  = parse_time("Order Time")
    start_time  = parse_time("Fulfillment Start Time")
    finish_time = parse_time("Order Completion Time")

    def safe_dur(start, end):
        dur = (end - start).dt.total_seconds() / 60
        # If negative it's a data entry error — set to None
        # Do NOT add 1440 — that makes bad data worse
        dur = dur.where(dur >= 0, None)
        # Cap at 90 minutes — anything above is outlier or data error
        dur = dur.where(dur <= 90, None)
        return dur

    df["Total Duration (mins)"]      = safe_dur(order_time, finish_time)
    df["Initiation Duration (mins)"] = safe_dur(order_time, start_time)

    if "Delivery Duration (mins)" not in df.columns or df["Delivery Duration (mins)"].isna().all():
        df["Delivery Duration (mins)"] = safe_dur(start_time, finish_time)

    # On-time flag — 10 minute threshold
    df["On Time"] = df["Delivery Duration (mins)"].apply(
        lambda x: x <= 10 if pd.notna(x) else None
    )

    # Free vs Paid delivery
    df["Delivery Type"] = df[
        "Delivery Fee (Amount we Collected from the customer)"
    ].apply(lambda x: "Free" if pd.notna(x) and x == 0 else "Paid")

    # Order hour for hourly pattern chart
    df["Order Hour"] = order_time.dt.hour

    return df


# ============================================================
# LOAD GOOGLE SHEETS ORDERS
# Historical data — Jan 2026 to Jul 31 2026 only.
# Filtered by Date of Order column (not Timestamp).
# ============================================================
def load_sheets_orders():
    try:
        df = fetch_csv(ORDERS_URL)
        df.columns = df.columns.str.strip()
        df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

        # Convert Date of Order first so we can filter
        df["Date of Order"] = pd.to_datetime(df["Date of Order"], errors="coerce")
        df = df.dropna(subset=["Date of Order"])

        # Keep only orders BEFORE the cutoff date
        df = df[df["Date of Order"] < SUPABASE_CUTOFF]

        df["Data Source"] = "Google Sheets"
        df = clean_and_enrich(df)
        return df

    except Exception as e:
        st.warning(f"Google Sheets load failed: {e}")
        return pd.DataFrame()


# ============================================================
# LOAD SUPABASE ORDERS
# Live data — Aug 1 2026 onwards only.
# Status = 'closed' confirmed from database test.
# ============================================================
def load_supabase_orders():
    try:
        # Fetch closed orders from Aug 1 onwards
        orders_df = fetch_all_rows(
            "orders",
            select="id,created_at,customer_whatsapp,product,"
                   "rider_id,petrol_station_id,gas_station_id,"
                   "zone,rider_payout,delivery_fee,grand_total,"
                   "status,fulfillment_start,completion_time,"
                   "measured_delivery_time,is_member_free_delivery,"
                   "agent_order_id",
            eq_filter={"status": "closed"}
        )

        if orders_df.empty:
            return pd.DataFrame()

        # Convert created_at to date and filter from Aug 1 onwards
        orders_df["created_at_dt"] = pd.to_datetime(
            orders_df["created_at"], errors="coerce", utc=True
        ).dt.tz_convert("Africa/Lagos").dt.tz_localize(None)

        orders_df = orders_df[
            orders_df["created_at_dt"] >= SUPABASE_CUTOFF
        ]

        if orders_df.empty:
            return pd.DataFrame()

        # Fetch supporting tables
        items_df = fetch_all_rows(
            "order_items",
            select="order_id,quantity,cost_price,selling_price,cogs,gmv,revenue,profit"
        )
        customers_df = fetch_all_rows(
            "customers",
            select="whatsapp_number,name"
        )
        riders_df = fetch_all_rows(
            "riders",
            select="id,name"
        )
        stations_df = fetch_all_rows(
            "stations",
            select="id,station_name"
        )

        # Merge supporting tables
        if not items_df.empty:
            orders_df = orders_df.merge(
                items_df,
                left_on="id", right_on="order_id",
                how="left"
            )

        if not customers_df.empty:
            orders_df = orders_df.merge(
                customers_df,
                left_on="customer_whatsapp", right_on="whatsapp_number",
                how="left"
            )

        if not riders_df.empty:
            orders_df = orders_df.merge(
                riders_df.rename(columns={"id": "r_id", "name": "rider_name"}),
                left_on="rider_id", right_on="r_id",
                how="left"
            )

        if not stations_df.empty:
            orders_df = orders_df.merge(
                stations_df.rename(columns={"id": "ps_id", "station_name": "petrol_stn"}),
                left_on="petrol_station_id", right_on="ps_id",
                how="left"
            )
            orders_df = orders_df.merge(
                stations_df.rename(columns={"id": "gs_id", "station_name": "gas_stn"}),
                left_on="gas_station_id", right_on="gs_id",
                how="left"
            )

        # Map product names to match Google Sheets format
        product_map = {
            "gas":    "Gas (LPG)",
            "petrol": "Petrol (PMS)",
            "oil":    "Engine Oil"
        }
        orders_df["product"] = orders_df["product"].str.lower().map(
            product_map
        ).fillna(orders_df["product"])

        # Clean zone names — strip suffixes like "(before T-junction)"
        orders_df["zone"] = orders_df["zone"].fillna("Unknown").str.split(
            r'\(', expand=True, regex=True
        )[0].str.strip()

        # Rename to dashboard standard column names
        orders_df["Order ID"] = orders_df["agent_order_id"].fillna(
            orders_df["id"].astype(str)
        )
        orders_df["Date of Order"] = orders_df["created_at_dt"].dt.strftime("%Y-%m-%d")
        orders_df["Day of the Week"] = orders_df["created_at_dt"].dt.strftime("%a")
        orders_df["Order Type"]      = orders_df["product"]
        orders_df["Litre/Kg Sold"]   = pd.to_numeric(orders_df.get("quantity", 0), errors="coerce").fillna(0)
        orders_df["Cost Price (Per kg/liter)"]    = pd.to_numeric(orders_df.get("cost_price", 0), errors="coerce").fillna(0)
        orders_df["Selling Price (Per kg/Liter)"] = pd.to_numeric(orders_df.get("selling_price", 0), errors="coerce").fillna(0)
        orders_df["Customer Name"]       = orders_df.get("name", orders_df["customer_whatsapp"]).fillna(orders_df["customer_whatsapp"])
        orders_df["Customer Phone"]      = orders_df["customer_whatsapp"]
        orders_df["Order Area/Location"] = orders_df["zone"]
        orders_df["Rider Name"]          = orders_df.get("rider_name", pd.Series("Unknown", index=orders_df.index)).fillna("Unknown")
        orders_df["Station"]             = orders_df.get("petrol_stn", pd.Series("Unknown", index=orders_df.index)).fillna(
            orders_df.get("gas_stn", pd.Series("Unknown", index=orders_df.index))
        ).fillna("Unknown")

        # --------------------------------------------------------
        # TIME COLUMNS
        # Store as string for display purposes only.
        # --------------------------------------------------------
        orders_df["Order Time"] = orders_df["created_at_dt"].dt.strftime("%I:%M:%S %p")

        # Parse full timestamps for accurate duration calculation
        fulfillment_dt = pd.to_datetime(
            orders_df["fulfillment_start"], errors="coerce", utc=True
        ).dt.tz_convert("Africa/Lagos").dt.tz_localize(None)

        completion_dt = pd.to_datetime(
            orders_df["completion_time"], errors="coerce", utc=True
        ).dt.tz_convert("Africa/Lagos").dt.tz_localize(None)

        orders_df["Fulfillment Start Time"] = fulfillment_dt.dt.strftime("%I:%M:%S %p")
        orders_df["Order Completion Time"]  = completion_dt.dt.strftime("%I:%M:%S %p")

        # --------------------------------------------------------
        # CALCULATE DELIVERY DURATIONS FROM FULL TIMESTAMPS
        # Using full datetime objects NOT time strings.
        # This correctly handles midnight crossovers and
        # multi-hour orders without any calculation errors.
        # --------------------------------------------------------

        # Total duration: order placed to completion
        orders_df["Total Duration (mins)"] = (
            completion_dt - orders_df["created_at_dt"]
        ).dt.total_seconds() / 60

        # Initiation duration: order placed to fulfillment start
        orders_df["Initiation Duration (mins)"] = (
            fulfillment_dt - orders_df["created_at_dt"]
        ).dt.total_seconds() / 60

        # Delivery duration: fulfillment start to completion
        orders_df["Delivery Duration (mins)"] = (
            completion_dt - fulfillment_dt
        ).dt.total_seconds() / 60

        # Remove negative durations — data entry errors
        for col in ["Total Duration (mins)", "Initiation Duration (mins)", "Delivery Duration (mins)"]:
            orders_df.loc[orders_df[col] < 0, col] = None
            # Remove extreme outliers over 24 hours — likely data errors
            orders_df.loc[orders_df[col] > 1440, col] = None


            # Remove negative durations — data entry errors
        # Cap at 120 minutes — anything above is a forgotten close or data error
        for col in ["Total Duration (mins)", "Initiation Duration (mins)", "Delivery Duration (mins)"]:
            orders_df.loc[orders_df[col] < 0, col] = None
            orders_df.loc[orders_df[col] > 90, col] = None


        # Financial columns
        orders_df["Delivery Cost (how much we paid to the Rider)"] = pd.to_numeric(
            orders_df.get("rider_payout", 0), errors="coerce"
        ).fillna(0)
        orders_df["Delivery Fee (Amount we Collected from the customer)"] = pd.to_numeric(
            orders_df.get("delivery_fee", 0), errors="coerce"
        ).fillna(0)

        gmv_series = pd.to_numeric(orders_df.get("gmv", orders_df["grand_total"]), errors="coerce")
        grand_series = pd.to_numeric(orders_df["grand_total"], errors="coerce")
        orders_df["Revenue (Total Customer Payment)"] = gmv_series.fillna(grand_series)

        orders_df["COGS(naira)"] = pd.to_numeric(
            orders_df.get("cogs", pd.Series(0, index=orders_df.index)),
            errors="coerce"
        ).fillna(0)
        orders_df["Revenue"] = pd.to_numeric(
            orders_df.get("revenue", pd.Series(0, index=orders_df.index)),
            errors="coerce"
        ).fillna(0)
        orders_df["Profit"] = pd.to_numeric(
            orders_df.get("profit", pd.Series(0, index=orders_df.index)),
            errors="coerce"
        ).fillna(0)
        orders_df["Delivery Duration (mins)"] = pd.to_numeric(
            orders_df.get("measured_delivery_time"),
            errors="coerce"
        )
        orders_df["Data Source"] = "Supabase"

        # Keep only standard columns
        keep_cols = [
            "Order ID", "Date of Order", "Day of the Week",
            "Order Type", "Litre/Kg Sold",
            "Cost Price (Per kg/liter)", "Selling Price (Per kg/Liter)",
            "Customer Name", "Customer Phone", "Order Area/Location",
            "Rider Name", "Station",
            "Order Time", "Fulfillment Start Time", "Order Completion Time",
            "Delivery Cost (how much we paid to the Rider)",
            "Delivery Fee (Amount we Collected from the customer)",
            "Revenue (Total Customer Payment)", "COGS(naira)",
            "Revenue", "Profit",
            "Delivery Duration (mins)", "Data Source"
        ]
        orders_df = orders_df[[c for c in keep_cols if c in orders_df.columns]]
        orders_df = clean_and_enrich(orders_df)
        return orders_df

    except Exception as e:
        st.warning(f"Supabase load failed: {e}")
        return pd.DataFrame()


# ============================================================
# LOAD ORDERS — MERGED WITH CLEAN DATE CUTOFF
# Google Sheets: Jan 2026 to Jul 31 2026
# Supabase: Aug 1 2026 onwards
# No overlap possible. No deduplication needed.
# ============================================================
@st.cache_data(ttl=600)
def load_orders():

    sheets_df   = load_sheets_orders()
    supabase_df = load_supabase_orders()

    if sheets_df.empty and supabase_df.empty:
        st.error("No data loaded from either source.")
        return pd.DataFrame()

    if sheets_df.empty:
        return supabase_df

    if supabase_df.empty:
        return sheets_df

    # Clean merge — no overlap possible due to date cutoff
    merged = pd.concat([sheets_df, supabase_df], ignore_index=True)
    merged = merged.sort_values("Date of Order").reset_index(drop=True)
    return merged


# ============================================================
# LOAD TARGETS — Always from Google Sheets
# Supabase ops_targets is empty so Sheets is permanent source.
# ============================================================
@st.cache_data(ttl=600)
def load_targets():
    df = fetch_csv(TARGETS_URL)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df.columns = df.columns.str.strip()
    df["Period"] = pd.to_datetime(df["Period"], errors="coerce")
    for col in ["Target GMV", "Target Revenue", "Target Profit",
                "Target Orders", "Target Delivery Cost"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False),
                errors="coerce"
            )
    return df