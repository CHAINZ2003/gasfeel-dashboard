"""
GasFeel data-source diagnostic
Checks:
- Google Sheets orders before 2026-08-01
- Supabase closed orders from 2026-08-01 onward
- Revenue and order-count reconciliation
- Potential duplicate IDs and date-boundary issues

Install dependencies:
    pip install pandas requests supabase

Set your Supabase key in PowerShell before running:
    $env:SUPABASE_SECRET_KEY = "YOUR_REAL_SUPABASE_KEY"
    python test_data_split.py

Never commit your Supabase secret/service-role key to GitHub.
"""

import os
import sys
import pandas as pd
import requests
from io import StringIO
from supabase import create_client
from postgrest.exceptions import APIError


# ------------------------- CONFIGURATION -------------------------

SUPABASE_URL = "https://mvbcevkxcuexilqqksou.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY", "").strip()

ORDERS_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vS3CDt_ulHB-4JN80DKixskyHZhE_caf75oKICt-dirQNmBb3gH9WDNDVrkXY2Y0ja862OV1DXv3y72/"
    "pub?gid=1183636741&single=true&output=csv"
)

TABLE_NAME = "orders"
CUTOFF = pd.Timestamp("2026-08-01")  # Nigeria-local date boundary
EXPECTED_SUPABASE_ORDERS = 637
EXPECTED_SUPABASE_REVENUE = 5_665_145.00
DASHBOARD_ORDERS = 2_369
PAGE_SIZE = 1000

SHEETS_DATE_COLUMN = "Date of Order"
SHEETS_REVENUE_COLUMN = "Revenue (Total Customer Payment)"


def money(series):
    """Convert numbers stored as text, possibly with commas or currency symbols."""
    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("₦", "", regex=False)
        .str.replace("NGN", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="coerce")


def print_money(label, value):
    print(f"{label}: ₦{value:,.2f}")


def find_id_column(columns):
    """Find a likely order identifier column without assuming one exact name."""
    candidates = [
        "Order ID", "Order Id", "order_id", "order_number",
        "Order Number", "ID", "id", "agent_order_id"
    ]
    normalized = {str(c).strip().lower(): c for c in columns}
    for candidate in candidates:
        match = normalized.get(candidate.lower())
        if match is not None:
            return match
    return None


def main():
    # ------------------------- CHECK KEY -------------------------
    if not SUPABASE_KEY:
        print("ERROR: SUPABASE_SECRET_KEY is not set.")
        print("In PowerShell, run:")
        print('  $env:SUPABASE_SECRET_KEY = "YOUR_REAL_SUPABASE_KEY"')
        print("Then run:")
        print("  python test_data_split.py")
        sys.exit(1)

    # ------------------------- TEST 1: GOOGLE SHEETS -------------------------
    print("\n" + "=" * 64)
    print("TEST 1 — GOOGLE SHEETS")
    print("=" * 64)

    try:
        response = requests.get(
            ORDERS_URL,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        response.raise_for_status()
        sheets_df = pd.read_csv(StringIO(response.text))
    except Exception as exc:
        print(f"Could not download/read Google Sheets CSV: {exc}")
        sys.exit(1)

    sheets_df.columns = sheets_df.columns.astype(str).str.strip()
    sheets_df = sheets_df.loc[
        :, ~sheets_df.columns.str.startswith("Unnamed")
    ].copy()

    missing_columns = [
        col for col in [SHEETS_DATE_COLUMN, SHEETS_REVENUE_COLUMN]
        if col not in sheets_df.columns
    ]
    if missing_columns:
        print("ERROR: Required Google Sheets column(s) not found:", missing_columns)
        print("Columns found:", list(sheets_df.columns))
        sys.exit(1)

    # Parse sheet dates. Invalid dates are reported rather than silently counted.
    sheets_df[SHEETS_DATE_COLUMN] = pd.to_datetime(
        sheets_df[SHEETS_DATE_COLUMN], errors="coerce"
    )
    invalid_sheet_dates = int(sheets_df[SHEETS_DATE_COLUMN].isna().sum())
    sheets_df = sheets_df.dropna(subset=[SHEETS_DATE_COLUMN]).copy()

    # Remove timezone information if present, keeping the parsed displayed date.
    if getattr(sheets_df[SHEETS_DATE_COLUMN].dt, "tz", None) is not None:
        sheets_df[SHEETS_DATE_COLUMN] = (
            sheets_df[SHEETS_DATE_COLUMN].dt.tz_convert("Africa/Lagos").dt.tz_localize(None)
        )

    sheets_df[SHEETS_REVENUE_COLUMN] = money(
        sheets_df[SHEETS_REVENUE_COLUMN]
    )

    sheets_before = sheets_df[
        sheets_df[SHEETS_DATE_COLUMN] < CUTOFF
    ].copy()
    sheets_onward = sheets_df[
        sheets_df[SHEETS_DATE_COLUMN] >= CUTOFF
    ].copy()

    print(f"Rows downloaded from Google Sheets: {len(sheets_df):,}")
    print(f"Rows with invalid/missing order dates: {invalid_sheet_dates:,}")
    print(f"Rows before 2026-08-01 (assigned to Sheets): {len(sheets_before):,}")
    print(f"Rows on/after 2026-08-01 (excluded from Sheets): {len(sheets_onward):,}")
    print_money(
        "Sheets revenue before cutoff",
        sheets_before[SHEETS_REVENUE_COLUMN].sum()
    )
    print(
        "Missing/unparseable Sheets revenue values before cutoff:",
        int(sheets_before[SHEETS_REVENUE_COLUMN].isna().sum())
    )

    sheets_id_col = find_id_column(sheets_before.columns)
    if sheets_id_col:
        nonblank_ids = sheets_before[sheets_id_col].dropna().astype(str).str.strip()
        nonblank_ids = nonblank_ids[nonblank_ids.ne("")]
        print(f"Possible Sheets order-ID column: {sheets_id_col}")
        print(f"Unique nonblank IDs before cutoff: {nonblank_ids.nunique():,}")
        print(f"Repeated IDs beyond first occurrence: {len(nonblank_ids) - nonblank_ids.nunique():,}")
    else:
        print("No obvious Sheets order-ID column detected; row count may include duplicates.")

    # Show status distribution if the sheet has a likely status field.
    status_cols = [
        c for c in sheets_before.columns
        if str(c).strip().lower() in {"status", "order status", "order_status"}
    ]
    if status_cols:
        status_col = status_cols[0]
        print(f"\nSheets status breakdown ({status_col}):")
        print(
            sheets_before[status_col]
            .fillna("(blank)")
            .astype(str)
            .str.strip()
            .value_counts(dropna=False)
            .to_string()
        )

    # ------------------------- TEST 2: SUPABASE -------------------------
    print("\n" + "=" * 64)
    print("TEST 2 — SUPABASE")
    print("=" * 64)

    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        all_rows = []
        offset = 0

        while True:
            result = (
                supabase.table(TABLE_NAME)
                .select("id,created_at,grand_total,status,agent_order_id")
                .eq("status", "closed")
                .order("created_at")
                .range(offset, offset + PAGE_SIZE - 1)
                .execute()
            )

            batch = result.data or []
            if not batch:
                break

            all_rows.extend(batch)
            print(f"Fetched Supabase rows: {len(all_rows):,}", end="\r")

            if len(batch) < PAGE_SIZE:
                break
            offset += PAGE_SIZE

    except APIError as exc:
        print("\nSupabase API error. Check the URL, API key, table name, and permissions.")
        print(f"Details: {exc}")
        sys.exit(1)
    except Exception as exc:
        print("\nCould not query Supabase.")
        print(f"Error type: {type(exc).__name__}")
        print(f"Details: {exc}")
        sys.exit(1)

    print()
    if not all_rows:
        print("Supabase returned zero closed orders. Verify status values and access.")
        sys.exit(1)

    supa_df = pd.DataFrame(all_rows)
    supa_df["created_at_dt"] = pd.to_datetime(
        supa_df["created_at"], errors="coerce", utc=True
    ).dt.tz_convert("Africa/Lagos").dt.tz_localize(None)
    supa_df["grand_total"] = money(supa_df["grand_total"])

    invalid_supa_dates = int(supa_df["created_at_dt"].isna().sum())
    supa_df = supa_df.dropna(subset=["created_at_dt"]).copy()

    supa_before = supa_df[supa_df["created_at_dt"] < CUTOFF].copy()
    supa_onward = supa_df[supa_df["created_at_dt"] >= CUTOFF].copy()

    print(f"All closed Supabase orders fetched: {len(supa_df):,}")
    print(f"Closed orders with invalid created_at: {invalid_supa_dates:,}")
    print(f"Closed orders before 2026-08-01 (excluded from Supabase): {len(supa_before):,}")
    print(f"Closed orders on/after 2026-08-01: {len(supa_onward):,}")
    print_money("Supabase revenue on/after cutoff", supa_onward["grand_total"].sum())
    print(
        "Missing/unparseable Supabase grand_total values on/after cutoff:",
        int(supa_onward["grand_total"].isna().sum())
    )
    print(
        "Unique Supabase order IDs on/after cutoff:",
        supa_onward["id"].nunique()
    )

    print("\nSupabase comparison with expected SQL figures:")
    print(f"Expected orders: {EXPECTED_SUPABASE_ORDERS:,}")
    print(f"Actual orders:   {len(supa_onward):,}")
    print(f"Order difference: {len(supa_onward) - EXPECTED_SUPABASE_ORDERS:+,}")
    print_money("Expected revenue", EXPECTED_SUPABASE_REVENUE)
    print_money("Actual revenue", supa_onward["grand_total"].sum())
    print_money(
        "Revenue difference",
        supa_onward["grand_total"].sum() - EXPECTED_SUPABASE_REVENUE
    )

    # ------------------------- TEST 3: RECONCILIATION -------------------------
    print("\n" + "=" * 64)
    print("TEST 3 — COMBINED DASHBOARD RECONCILIATION")
    print("=" * 64)

    combined_orders = len(sheets_before) + len(supa_onward)
    combined_revenue = (
        sheets_before[SHEETS_REVENUE_COLUMN].sum()
        + supa_onward["grand_total"].sum()
    )

    print(f"Google Sheets rows before cutoff: {len(sheets_before):,}")
    print(f"Supabase closed orders from cutoff: {len(supa_onward):,}")
    print(f"Combined row/order count (raw): {combined_orders:,}")
    print(f"Dashboard currently reports: {DASHBOARD_ORDERS:,}")
    print(f"Dashboard count minus raw combined count: {DASHBOARD_ORDERS - combined_orders:+,}")
    print_money("Combined GMV/revenue field total", combined_revenue)

    if sheets_id_col:
        sheets_ids = (
            sheets_before[sheets_id_col]
            .dropna().astype(str).str.strip()
        )
        sheets_ids = set(sheets_ids[sheets_ids.ne("")])
        supa_agent_ids = set(
            supa_onward["agent_order_id"]
            .dropna().astype(str).str.strip()
        )
        supa_agent_ids.discard("")
        overlap = sheets_ids.intersection(supa_agent_ids)
        print(f"Possible IDs shared by Sheets and Supabase: {len(overlap):,}")
        if overlap:
            print("WARNING: Shared IDs may indicate cross-source duplicates.")
    else:
        print("Cross-source duplicate check skipped: no obvious Sheets ID column.")

    print("\nDiagnostic complete.")
    print("Important: this compares raw Sheets rows with Supabase status='closed'.")
    print("If the dashboard excludes cancelled, duplicate, or unpaid Sheets rows,")
    print("apply the same rules here before expecting exact count equality.")


if __name__ == "__main__":
    main()
