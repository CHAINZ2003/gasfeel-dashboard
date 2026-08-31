# ============================================================
# DATA LOADER — GasFeel Dashboard
# DUAL SOURCE with clean date cutoff:
# Google Sheets → Jan 2026 to Jul 31 2026 (historical)
# Supabase      → Aug 1 2026 onwards (live app data)
# No overlap. No duplicates. Clean merge.
# ============================================================

import pandas as pd
import streamlit as st
import requests
from io import StringIO
from supabase import create_client


# ============================================================
# CUTOFF DATE
# Everything before this date = Google Sheets
# Everything from this date onwards = Supabase
# ============================================================
SUPABASE_CUTOFF = pd.Timestamp("2026-08-01")


# ============================================================
# GOOGLE SHEETS URLs — Historical data + Targets
# ============================================================
ORDERS_URL  = st.secrets["ORDERS_URL"]
TARGETS_URL = st.secrets["TARGETS_URL"]


# ============================================================
# SUPABASE CLIENT
# Uses service_role key to bypass RLS and see all data.
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
# HELPER — SAFE NUMERIC CONVERSION
# Converts a column to float safely, filling nulls with 0.
# ============================================================
def safe_num(series, fill=0):
    return pd.to_numeric(series, errors="coerce").fillna(fill)


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
    # --------------------------------------------------------
    df["Date of Order"] = pd.to_datetime(df["Date of Order"], errors="coerce")
    df = df.dropna(subset=["Date of Order"])

    # Extract time period columns for filters
    df["Month"]      = df["Date of Order"].dt.month
    df["Month Name"] = df["Date of Order"].dt.strftime("%B")
    df["Year"]       = df["Date of Order"].dt.year
    df["Week"]       = df["Date of Order"].dt.isocalendar().week.astype("Int64")

    # Clean text columns
    text_cols = [
        "Customer Name", "Rider Name",
        "Order Area/Location", "Station", "Order Type"
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()
            df[col] = df[col].replace("Nan", None)

    # Clean numeric columns for Google Sheets source
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
    df["GMV"] = safe_num(df["Revenue (Total Customer Payment)"])

    if "Revenue" not in df.columns or df["Revenue"].isna().all():
        df["Revenue"] = df["GMV"] - safe_num(df.get("COGS(naira)", pd.Series(0, index=df.index)))

    if "Profit" not in df.columns or df["Profit"].isna().all():
        df["Profit"] = df["Revenue"] - safe_num(
            df.get("Delivery Cost (how much we paid to the Rider)", pd.Series(0, index=df.index))
        )

    # --------------------------------------------------------
    # DELIVERY TIME CALCULATIONS
    # Initiation = Fulfillment Start - Order Time
    # Delivery   = Order Completion - Fulfillment Start
    # Total      = Order Completion - Order Time
    # Cap at 90 mins — above is outlier or data error
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
        dur = dur.where(dur >= 0, None)
        dur = dur.where(dur <= 90, None)
        return dur

    df["Initiation Duration (mins)"] = safe_dur(order_time, start_time)
    df["Delivery Duration (mins)"]   = safe_dur(start_time, finish_time)
    df["Total Duration (mins)"]      = safe_dur(order_time, finish_time)

    # On-time flag — 10 minute threshold on TOTAL journey
    df["On Time"] = df["Total Duration (mins)"].apply(
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
# LOAD GOOGLE SHEETS ORDERS — Historical data
# Jan 2026 to Jul 31 2026 only.
# ============================================================
def load_sheets_orders():
    try:
        df = fetch_csv(ORDERS_URL)
        df.columns = df.columns.str.strip()
        df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

        # Convert date and filter before cutoff
        df["Date of Order"] = pd.to_datetime(df["Date of Order"], errors="coerce")
        df = df.dropna(subset=["Date of Order"])
        df = df[df["Date of Order"] < SUPABASE_CUTOFF]

        df["Data Source"] = "Google Sheets"
        df = clean_and_enrich(df)
        return df

    except Exception as e:
        st.warning(f"Google Sheets load failed: {e}")
        return pd.DataFrame()


# ============================================================
# LOAD SUPABASE ORDERS — Live app data from Aug 1 2026
# ============================================================
def load_supabase_orders():
    try:
        # --------------------------------------------------------
        # FETCH CLOSED ORDERS
        # --------------------------------------------------------
        orders_df = fetch_all_rows(
            "orders",
            select="id,created_at,customer_whatsapp,product,"
                   "rider_id,petrol_station_id,gas_station_id,"
                   "zone,rider_payout,delivery_fee,grand_total,"
                   "cost_price,margin,vat,deposit_used,"
                   "status,fulfillment_start,completion_time,"
                   "measured_delivery_time,is_member_free_delivery,"
                   "agent_order_id",
            eq_filter={"status": "closed"}
        )

        if orders_df.empty:
            return pd.DataFrame()

        # --------------------------------------------------------
        # CONVERT TIMESTAMPS TO LAGOS TIME
        # --------------------------------------------------------
        orders_df["created_at_dt"] = pd.to_datetime(
            orders_df["created_at"], errors="coerce", utc=True, format="ISO8601"
        ).dt.tz_convert("Africa/Lagos").dt.tz_localize(None)

        # Filter from Aug 1 2026 onwards
        orders_df = orders_df[orders_df["created_at_dt"] >= SUPABASE_CUTOFF]

        if orders_df.empty:
            return pd.DataFrame()

        # --------------------------------------------------------
        # FETCH SUPPORTING TABLES
        # --------------------------------------------------------
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

        # --------------------------------------------------------
        # MERGE SUPPORTING TABLES
        # --------------------------------------------------------
        if not customers_df.empty:
            orders_df = orders_df.merge(
                customers_df,
                left_on="customer_whatsapp",
                right_on="whatsapp_number",
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

        # --------------------------------------------------------
        # MAP PRODUCT NAMES to match Google Sheets format
        # --------------------------------------------------------
        product_map = {
            "gas":    "Gas (LPG)",
            "petrol": "Petrol (PMS)",
            "oil":    "Engine Oil"
        }
        orders_df["product"] = orders_df["product"].astype(str).str.lower().map(
            product_map
        ).fillna(orders_df["product"])

        # --------------------------------------------------------
        # CLEAN ZONE NAMES
        # Strip suffixes like "(before T-junction)"
        # --------------------------------------------------------
        orders_df["zone"] = orders_df["zone"].fillna("Unknown").astype(str).str.split(
            r'\(', expand=True, regex=True
        )[0].str.strip()

        # --------------------------------------------------------
        # PARSE FULFILLMENT AND COMPLETION TIMESTAMPS
        # Use full datetime objects for accurate duration calculation
        # --------------------------------------------------------
        fulfillment_dt = pd.to_datetime(
            orders_df["fulfillment_start"],
            errors="coerce", utc=True, format="ISO8601"
        ).dt.tz_convert("Africa/Lagos").dt.tz_localize(None)

        completion_dt = pd.to_datetime(
            orders_df["completion_time"],
            errors="coerce", utc=True, format="ISO8601"
        ).dt.tz_convert("Africa/Lagos").dt.tz_localize(None)

        # --------------------------------------------------------
        # RENAME TO DASHBOARD STANDARD COLUMN NAMES
        # --------------------------------------------------------
        orders_df["Order ID"] = orders_df["agent_order_id"].fillna(
            orders_df["id"].astype(str)
        )
        orders_df["Date of Order"]    = orders_df["created_at_dt"].dt.strftime("%Y-%m-%d")
        orders_df["Day of the Week"]  = orders_df["created_at_dt"].dt.strftime("%a")
        orders_df["Order Type"]       = orders_df["product"]
        orders_df["Customer Name"]    = orders_df.get(
            "name", orders_df["customer_whatsapp"]
        ).fillna(orders_df["customer_whatsapp"])
        orders_df["Customer Phone"]      = orders_df["customer_whatsapp"]
        orders_df["Order Area/Location"] = orders_df["zone"]
        orders_df["Rider Name"]          = orders_df.get(
            "rider_name", pd.Series("Unknown", index=orders_df.index)
        ).fillna("Unknown")

        # Station — use petrol station, fall back to gas station
        petrol_stn = orders_df.get("petrol_stn", pd.Series(dtype=str))
        gas_stn    = orders_df.get("gas_stn", pd.Series(dtype=str))
        orders_df["Station"] = petrol_stn.fillna(gas_stn).fillna("Unknown")

        # Time columns for display only
        orders_df["Order Time"] = orders_df["created_at_dt"].dt.strftime("%I:%M:%S %p")
        orders_df["Fulfillment Start Time"] = fulfillment_dt.dt.strftime("%I:%M:%S %p")
        orders_df["Order Completion Time"]  = completion_dt.dt.strftime("%I:%M:%S %p")

        # Quantity and price
        orders_df["Litre/Kg Sold"] = safe_num(
            orders_df.get("quantity", pd.Series(0, index=orders_df.index))
        )
        orders_df["Cost Price (Per kg/liter)"] = safe_num(
            orders_df.get("cost_price_y", orders_df.get("cost_price", pd.Series(0, index=orders_df.index)))
        )
        orders_df["Selling Price (Per kg/Liter)"] = safe_num(
            orders_df.get("selling_price", pd.Series(0, index=orders_df.index))
        )

        # --------------------------------------------------------
        # FINANCIAL MODEL — Supabase
        # GMV     = grand_total (full customer payment)
        # COGS    = cost_price from orders table
        # Revenue = GMV - COGS
        # Profit  = Revenue - rider_payout
        # --------------------------------------------------------
        grand_total  = safe_num(orders_df["grand_total"])
        cost_price   = safe_num(orders_df.get("cost_price", pd.Series(0, index=orders_df.index)))
        rider_payout = safe_num(orders_df.get("rider_payout", pd.Series(0, index=orders_df.index)))
        delivery_fee = safe_num(orders_df.get("delivery_fee", pd.Series(0, index=orders_df.index)))
        

        orders_df["Revenue (Total Customer Payment)"] = grand_total
        orders_df["COGS(naira)"]  = cost_price
        orders_df["GMV"]          = grand_total
        orders_df["Revenue"]      = grand_total - cost_price
        orders_df["Profit"]       = grand_total - cost_price - rider_payout
        orders_df["Delivery Cost (how much we paid to the Rider)"] = rider_payout
        orders_df["Delivery Fee (Amount we Collected from the customer)"] = delivery_fee

        # --------------------------------------------------------
        # DELIVERY TIME FROM FULL TIMESTAMPS
        # Initiation = Fulfillment Start - Order Time
        # Delivery   = Completion - Fulfillment Start
        # Total      = Completion - Order Time
        # Cap at 90 mins
        # --------------------------------------------------------
        def calc_dur(start, end):
            dur = (end - start).dt.total_seconds() / 60
            dur = dur.where(dur >= 0, None)
            dur = dur.where(dur <= 90, None)
            return dur

        orders_df["Initiation Duration (mins)"] = calc_dur(
            orders_df["created_at_dt"], fulfillment_dt
        )
        orders_df["Delivery Duration (mins)"] = calc_dur(
            fulfillment_dt, completion_dt
        )
        orders_df["Total Duration (mins)"] = calc_dur(
            orders_df["created_at_dt"], completion_dt
        )

        # On-time flag — 10 minute threshold on TOTAL journey
        orders_df["On Time"] = orders_df["Total Duration (mins)"].apply(
            lambda x: x <= 10 if pd.notna(x) else None
        )

        # Free vs Paid delivery
        orders_df["Delivery Type"] = delivery_fee.apply(
            lambda x: "Free" if x == 0 else "Paid"
        )

        orders_df["Data Source"] = "Supabase"

        # --------------------------------------------------------
        # KEEP ONLY STANDARD COLUMNS
        # --------------------------------------------------------
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
            "GMV", "Revenue", "Profit",
            "Initiation Duration (mins)", "Delivery Duration (mins)",
            "Total Duration (mins)", "On Time", "Delivery Type",
            "Data Source"
        ]
        orders_df = orders_df[[c for c in keep_cols if c in orders_df.columns]]

        # Apply standard cleaning
        orders_df = clean_and_enrich(orders_df)
        return orders_df

    except Exception as e:
        st.warning(f"Supabase load failed: {e}")
        return pd.DataFrame()


# ============================================================
# LOAD ORDERS — MERGED FROM BOTH SOURCES
# Google Sheets: Jan 2026 to Jul 31 2026
# Supabase: Aug 1 2026 onwards
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
# Supabase ops_targets is empty.
# ============================================================
@st.cache_data(ttl=600)
def load_targets():
    try:
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
    except Exception as e:
        st.warning(f"Targets load failed: {e}")
        return pd.DataFrame()