# ============================================================
# CUSTOMER INTELLIGENCE TAB — GasFeel Dashboard
# Snapshot KPIs, run-out and reachout lists, membership,
# acquisition, deposits, Active Base Movement (Petrol & Gas recency
# buckets), New vs Returning and product frequency.
#
# Wiring in app.py:
#   render_customer_intelligence(filtered_df)
#   render_retention_cohort(filtered_df, full_orders_df=df)
#   render_product_frequency(filtered_df, full_orders_df=df)
# (df = full orders BEFORE the sidebar filters)
# ============================================================

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import pandas as pd
from datetime import timedelta
from supabase import create_client


# ============================================================
# HELPER — FORMAT NAIRA
# ============================================================
def format_naira(value):
    try:
        if pd.isna(value) or value == 0:
            return "₦0"
    except Exception:
        return "₦0"
    if value >= 1_000_000:
        return f"₦{value/1_000_000:.2f}M"
    elif value >= 1_000:
        return f"₦{value/1_000:.2f}K"
    else:
        return f"₦{value:,.0f}"


# ============================================================
# HELPER — CHART DESCRIPTION
# ============================================================
def chart_note(text):
    st.markdown(f"""
        <p style='color:#888;font-size:12px;font-style:italic;
                  margin:-8px 0 10px 0;line-height:1.5;'>
            💡 {text}
        </p>
    """, unsafe_allow_html=True)


# ============================================================
# HELPER — NORMALISE PHONE NUMBERS (last 10 digits)
# ============================================================
def normalise_phone(series):
    digits = series.astype(str).str.replace(r"\D", "", regex=True).str[-10:]
    return digits.where(digits.str.len() >= 7, other=pd.NA)


# ============================================================
# HELPER — UNIQUE CUSTOMER KEY
# Customer Name (lowercase) is the only identifier shared by both
# data sources (Sheets has no phone), so it is used everywhere.
# Rows without a usable name or date are dropped.
# ============================================================
def add_customer_key(df):
    df = df.copy()
    df["Date of Order"] = pd.to_datetime(df["Date of Order"], errors="coerce")
    name_key = (
        df["Customer Name"].astype(str).str.strip().str.lower()
        .replace({"": pd.NA, "none": pd.NA, "nan": pd.NA})
    )
    df["_key"] = name_key
    return df.dropna(subset=["Date of Order", "_key"])


# ============================================================
# HELPER — LOAD CUSTOMER DATA FROM SUPABASE
# ============================================================
@st.cache_data(ttl=600)
def load_customer_intelligence():
    try:
        supabase = create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_KEY"]
        )

        all_customers = []
        offset = 0
        while True:
            result = supabase.table("customers").select(
                "whatsapp_number,name,customer_type,is_member,"
                "membership_deliveries_used,membership_deliveries_total,"
                "deposit_balance,last_bought_date,run_out_date,"
                "next_reachout_date,acquisition_channel,usual_kg,"
                "daily_fuel_amount,owning_agent_id,is_active,"
                "created_at,primary_area_id"
            ).range(offset, offset + 999).execute()
            if not result.data:
                break
            all_customers.extend(result.data)
            if len(result.data) < 1000:
                break
            offset += 1000

        df = pd.DataFrame(all_customers)

        for col in ["last_bought_date", "run_out_date",
                    "next_reachout_date", "created_at"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        for col in ["deposit_balance", "usual_kg", "daily_fuel_amount",
                    "membership_deliveries_used", "membership_deliveries_total"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        return df

    except Exception as e:
        st.error(f"Failed to load customer intelligence: {e}")
        return pd.DataFrame()


# ============================================================
# MAIN RENDER FUNCTION — CUSTOMER INTELLIGENCE
# ============================================================
def render_customer_intelligence(orders_df):

    today        = pd.Timestamp.now().normalize()
    customers_df = load_customer_intelligence()

    if customers_df.empty:
        st.info("No customer intelligence data available.")
        return

    total_customers  = len(customers_df)
    member_customers = customers_df["is_member"].sum()
    total_deposit    = customers_df["deposit_balance"].sum()
    avg_deposit      = customers_df[
        customers_df["deposit_balance"] > 0
    ]["deposit_balance"].mean()

    running_out_soon = customers_df[
        (customers_df["run_out_date"] >= today) &
        (customers_df["run_out_date"] <= today + timedelta(days=7))
    ]
    reachout_due = customers_df[
        customers_df["next_reachout_date"].notna() &
        (customers_df["next_reachout_date"] <= today)
    ]
    mem_util = (
        customers_df["membership_deliveries_used"].sum() /
        customers_df["membership_deliveries_total"].sum() * 100
        if customers_df["membership_deliveries_total"].sum() > 0 else 0
    )

    # ---------------- SECTION 1 — SNAPSHOT KPIs ----------------
    st.markdown(
        "<div class='section-title'>⚡ Customer Intelligence Snapshot</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "Live summary of your customer base from the Supabase database. "
        "Running Out Soon and Reachout Due are your most actionable numbers — "
        "these are customers who need to be contacted today."
    )

    def snap(label, value, sub=None, color="#003399"):
        sub_html = (
            f"<div style='font-size:11px;color:{color};font-weight:600;"
            f"margin-top:4px;'>{sub}</div>" if sub else ""
        )
        st.markdown(f"""
            <div style="background:white;border-radius:12px;padding:16px 14px;
                        box-shadow:0 4px 12px rgba(0,51,153,0.10);
                        border-top:4px solid {color};text-align:center;
                        margin-bottom:16px;">
                <div style="color:#999;font-size:10px;font-weight:700;
                            text-transform:uppercase;letter-spacing:1px;
                            margin-bottom:6px;">{label}</div>
                <div style="color:#001f6e;font-size:20px;font-weight:800;
                            line-height:1.1;">{value}</div>
                {sub_html}
            </div>
        """, unsafe_allow_html=True)

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1:
        snap("Total Customers", f"{total_customers:,}", "in database")
    with k2:
        snap("Active Members", f"{int(member_customers):,}",
             f"{(member_customers/total_customers*100):.1f}% of base")
    with k3:
        snap("Deposit Balance", format_naira(total_deposit),
             f"avg {format_naira(avg_deposit)}/customer")
    with k4:
        snap("Running Out Soon", f"{len(running_out_soon):,}", "within 7 days",
             "#cc0000" if len(running_out_soon) > 10 else "#f0a500")
    with k5:
        snap("Reachout Due", f"{len(reachout_due):,}",
             "today or overdue", "#f0a500")
    with k6:
        snap("Membership Utilization", f"{mem_util:.1f}%", "deliveries used")

    st.markdown("<br>", unsafe_allow_html=True)

    # ---------------- SECTION 2 — RUNNING OUT SOON ----------------
    st.markdown(
        "<div class='section-title'>🔴 Customers Running Out This Week — Call Now</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "Customers whose fuel or gas is expected to run out within 7 days. "
        "This is your highest-priority proactive sales list. "
        "Calling these customers before they run out increases conversion rate "
        "because they already know they need to reorder. "
        "Sorted by Days Until Empty — most urgent shown first."
    )

    if not running_out_soon.empty:
        runout_display = running_out_soon[[
            "name", "whatsapp_number", "customer_type",
            "usual_kg", "run_out_date", "last_bought_date"
        ]].copy()
        runout_display["Days Until Empty"] = (
            runout_display["run_out_date"] - today
        ).dt.days
        runout_display = runout_display.sort_values("Days Until Empty")
        runout_display["run_out_date"]     = runout_display["run_out_date"].dt.strftime("%d %b %Y")
        runout_display["last_bought_date"] = runout_display["last_bought_date"].dt.strftime("%d %b %Y")
        runout_display = runout_display.rename(columns={
            "name":             "Customer",
            "whatsapp_number":  "WhatsApp",
            "customer_type":    "Type",
            "usual_kg":         "Usual Qty",
            "run_out_date":     "Runs Out",
            "last_bought_date": "Last Order"
        })
        st.dataframe(runout_display, width="stretch", hide_index=True)
    else:
        st.success("No customers running out in the next 7 days.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ---------------- SECTION 3 — REACHOUT SCHEDULE ----------------
    st.markdown(
        "<div class='section-title'>📞 Reachout Due Today or Overdue</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "Customers whose scheduled follow-up date has passed. "
        "These are contacts that agents planned to reach out to "
        "but have not yet done so. "
        "Days Overdue = how many days past the planned date. "
        "Longer overdue = higher risk of losing that customer."
    )

    if not reachout_due.empty:
        reachout_display = reachout_due[[
            "name", "whatsapp_number", "customer_type",
            "next_reachout_date", "last_bought_date", "owning_agent_id"
        ]].copy()
        reachout_display["Days Overdue"] = (
            today - reachout_display["next_reachout_date"]
        ).dt.days
        reachout_display = reachout_display.sort_values(
            "Days Overdue", ascending=False
        )
        reachout_display["next_reachout_date"] = reachout_display[
            "next_reachout_date"
        ].dt.strftime("%d %b %Y")
        reachout_display["last_bought_date"] = pd.to_datetime(
            reachout_display["last_bought_date"], errors="coerce"
        ).dt.strftime("%d %b %Y")
        reachout_display = reachout_display.rename(columns={
            "name":               "Customer",
            "whatsapp_number":    "WhatsApp",
            "customer_type":      "Type",
            "next_reachout_date": "Due Date",
            "last_bought_date":   "Last Order",
            "owning_agent_id":    "Agent"
        })
        st.dataframe(reachout_display, width="stretch", hide_index=True)
    else:
        st.success("No reachouts overdue today.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ---------------- SECTION 4 — MEMBER VS NON-MEMBER ----------------
    st.markdown(
        "<div class='section-title'>👑 Member vs Non-Member Analysis</div>",
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            "<div class='section-title'>Customer Count</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Split between paying members and non-members. "
            "A growing member base means more predictable recurring revenue "
            "and lower churn risk since members have committed upfront."
        )
        member_counts = pd.DataFrame({
            "Status": ["Member", "Non-Member"],
            "Count":  [int(member_customers), int(total_customers - member_customers)]
        })
        fig_mem = px.pie(
            member_counts, names="Status", values="Count", hole=0.55,
            color_discrete_sequence=["#003399", "#ccd9ff"]
        )
        fig_mem.update_traces(textinfo="label+value+percent", textfont_size=11)
        fig_mem.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=5, r=5, t=20, b=5), height=280
        )
        st.plotly_chart(fig_mem, width="stretch")

    with col2:
        st.markdown(
            "<div class='section-title'>Revenue Split</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Revenue contribution from members vs non-members "
            "(for the period selected in the filter). "
            "Only orders with a phone number (Aug 2026 onward) can be matched "
            "to members; older Google Sheets orders count as non-member. "
            "If members generate a disproportionately large revenue share, "
            "the membership programme is working well."
        )

        if "Customer Phone" in orders_df.columns:
            orders_copy = orders_df.copy()   # never mutate the caller's data
            member_phones = set(
                normalise_phone(
                    customers_df[customers_df["is_member"] == True]["whatsapp_number"]
                ).dropna().tolist()
            )
            orders_copy["Is Member"] = normalise_phone(
                orders_copy["Customer Phone"]
            ).isin(member_phones)
            mem_rev = orders_copy.groupby("Is Member")["Revenue"].sum().reset_index()
            mem_rev["Status"] = mem_rev["Is Member"].map(
                {True: "Member", False: "Non-Member"}
            )
            fig_mem_rev = px.pie(
                mem_rev, names="Status", values="Revenue", hole=0.55,
                color_discrete_sequence=["#003399", "#ccd9ff"]
            )
            fig_mem_rev.update_traces(textinfo="label+percent", textfont_size=11)
            fig_mem_rev.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=5, r=5, t=20, b=5), height=280
            )
            st.plotly_chart(fig_mem_rev, width="stretch")

    st.markdown("<br>", unsafe_allow_html=True)

    # ---------------- SECTION 5 — ACQUISITION + DEPOSITS ----------------
    st.markdown(
        "<div class='section-title'>📣 Acquisition & Deposit Analysis</div>",
        unsafe_allow_html=True
    )

    col3, col4 = st.columns(2)

    with col3:
        st.markdown(
            "<div class='section-title'>Acquisition Channel Breakdown</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "How customers first found or joined GasFeel. "
            "The longest bar is your most effective acquisition channel. "
            "Invest more in what is working and review channels "
            "that bring very few customers."
        )
        channel_counts = customers_df[
            customers_df["acquisition_channel"].notna()
        ]["acquisition_channel"].value_counts().reset_index()
        channel_counts.columns = ["Channel", "Customers"]

        if not channel_counts.empty:
            fig_channel = px.bar(
                channel_counts, x="Customers", y="Channel",
                orientation="h", text="Customers",
                color_discrete_sequence=["#003399"]
            )
            fig_channel.update_traces(
                textposition="outside", textfont=dict(size=10, color="#333333")
            )
            fig_channel.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=5, r=40, t=10, b=5),
                xaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
                yaxis=dict(showgrid=False, title=""),
                height=280
            )
            st.plotly_chart(fig_channel, width="stretch")
        else:
            st.info("No acquisition channel data yet.")

    with col4:
        st.markdown(
            "<div class='section-title'>💰 Deposit Balance Distribution</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "How deposit balances are distributed across customers. "
            "Most bars on the left = small deposits typical. "
            "Bars far right = high-value deposit holders — "
            "these customers have committed significant funds and "
            "are highly unlikely to churn."
        )
        deposit_customers = customers_df[customers_df["deposit_balance"] > 0]
        if not deposit_customers.empty:
            fig_deposit = px.histogram(
                deposit_customers, x="deposit_balance", nbins=20,
                color_discrete_sequence=["#003399"]
            )
            fig_deposit.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=5, r=5, t=10, b=5),
                xaxis=dict(showgrid=True, gridcolor="#f0f0f0",
                           title="Deposit Balance (₦)"),
                yaxis=dict(showgrid=True, gridcolor="#f0f0f0",
                           title="Number of Customers"),
                height=280
            )
            st.plotly_chart(fig_deposit, width="stretch")
        else:
            st.info("No deposit balance data yet.")


# ============================================================
# NEW vs RETURNING SUMMARY
# New          = first-ever order was in that period
# Returning    = ordered in that period, first ordered earlier
# Total Active = New + Returning (matches the Customer tab)
# Built from FULL history; the filter only picks which periods show.
# ============================================================
def new_vs_returning_summary(full_df, view_df, freq):

    full = add_customer_key(full_df)
    if full.empty:
        return None

    full["_period"] = full["Date of Order"].dt.to_period(freq)
    first_period = full.groupby("_key")["_period"].min()

    total = full.groupby("_period")["_key"].nunique()
    new   = first_period.value_counts()

    summary = pd.DataFrame({"New Customers": new, "Total Active": total})
    summary = summary.fillna(0).astype(int).sort_index()
    summary["Returning Customers"] = summary["Total Active"] - summary["New Customers"]
    summary["Returning %"] = (
        summary["Returning Customers"] / summary["Total Active"] * 100
    ).round(0).astype(int).astype(str) + "%"
    summary = summary[["New Customers", "Returning Customers",
                       "Total Active", "Returning %"]]

    view = pd.to_datetime(view_df["Date of Order"], errors="coerce").dropna()
    if not view.empty:
        summary = summary[summary.index.isin(view.dt.to_period(freq).unique())]

    summary.index = summary.index.astype(str)
    summary.index.name = "Period"
    return summary


# ============================================================
# ACTIVE BASE MOVEMENT — recency buckets, Petrol and Gas
#
# At every month-end (current month = month-to-date) each customer is
# placed in a recency bucket = days since their LAST order of that
# product. Petrol and Gas have different bucket definitions because
# their buying cycles differ. A bar = all customers in the base at that
# snapshot; the Y axis is the unique customer count.
#
# LOOKBACK_DAYS: the base at each snapshot = customers with an order of
# that product in the last LOOKBACK_DAYS days (like the 0-90 day base in
# the telecom reference chart). Set to None to keep every customer who
# has ever ordered (the At-Risk bucket then only ever grows).
# ============================================================
YEAR_START    = pd.Timestamp("2026-01-01")
LOOKBACK_DAYS = 90
SIDE_BY_SIDE  = True      # False = stack the Petrol and Gas charts vertically

RECENCY_BUCKETS = {
    "Petrol": [("Hyper-Active", 0, 7),  ("Active", 8, 14),
               ("Slipping", 15, 30),    ("At-Risk", 31, None)],
    "Gas":    [("Hyper-Active", 0, 14), ("Active", 15, 30),
               ("Slipping", 31, 45),    ("At-Risk", 46, None)],
}
BUCKET_ORDER = ["Hyper-Active", "Active", "Slipping", "At-Risk"]
BUCKET_STYLE = {          # (fill colour, text colour)
    "Hyper-Active": ("#0b3d91", "#ffffff"),
    "Active":       ("#6fa8ff", "#111111"),
    "Slipping":     ("#f0a500", "#111111"),
    "At-Risk":      ("#c0392b", "#ffffff"),
}
BAD_WHEN_UP = {"At-Risk"}   # for these buckets an increase is shown RED
UP_COLOR, DOWN_COLOR, FLAT_COLOR = "#0a8a3a", "#cc0000", "#666666"

# Background phases (month numbers of 2026): label, first month, last month, tint
PHASES = [
    ("Pre-sales-team baseline (Jan–Jun)", 1, 6,  "rgba(120,130,150,0.13)"),
    ("July<br>sales surge",               7, 7,  "rgba(10,138,58,0.16)"),
    ("Aug onward:<br>stabilisation",      8, 12, "rgba(240,165,0,0.15)"),
]
# Month pairs where the cohort "bleed" into At-Risk is drawn on the chart
BLEED_PAIRS = [(7, 8), (8, 9)]


def product_bucket(series):
    s = series.astype(str).str.lower()
    out = pd.Series("Other", index=series.index)
    out[s.str.contains("gas", na=False)] = "Gas"
    out[s.str.contains("petrol|pms", na=False)] = "Petrol"
    return out


def bucket_label(product, name):
    for nm, lo, hi in RECENCY_BUCKETS[product]:
        if nm == name:
            if hi is not None:
                return f"{name} ({lo}–{hi}d)"
            return f"{name} ({lo}–{LOOKBACK_DAYS}d)" if LOOKBACK_DAYS else f"{name} ({lo}d+)"
    return name


def change_colour(ch, bucket=None):
    if ch == 0:
        return FLAT_COLOR
    good = ch > 0
    if bucket in BAD_WHEN_UP:
        good = not good
    return UP_COLOR if good else DOWN_COLOR


def _product_orders(full_df, product, today):
    full = add_customer_key(full_df)
    if full.empty:
        return None
    full["_d"] = full["Date of Order"].dt.normalize()
    full = full[(full["_d"] >= YEAR_START) & (full["_d"] <= today)]
    full = full[product_bucket(full["Order Type"]) == product]
    return full if not full.empty else None


def build_recency(full_df, product, today):
    """Returns (counts, assign, snaps) or None.
    counts : rows = month, cols = bucket names, value = unique customers
    assign : {month: Series(customer key -> bucket)}
    snaps  : [(month, snapshot date)]"""
    full = _product_orders(full_df, product, today)
    if full is None:
        return None

    defs  = RECENCY_BUCKETS[product]
    names = [d[0] for d in defs]
    edges = [-1] + [d[2] for d in defs[:-1]] + [np.inf]

    snaps = []
    for p in pd.period_range(YEAR_START.to_period("M"), today.to_period("M"), freq="M"):
        snaps.append((p, min(p.end_time.normalize(), today)))

    rows, assign = {}, {}
    for p, snap in snaps:
        last = full[full["_d"] <= snap].groupby("_key")["_d"].max()
        days = (snap - last).dt.days if len(last) else pd.Series([], dtype=int)
        if LOOKBACK_DAYS:
            days = days[days <= LOOKBACK_DAYS]
        if len(days):
            b = pd.cut(days, bins=edges, labels=names)
            assign[p] = b
            rows[p] = b.value_counts().reindex(names).fillna(0).astype(int)
        else:
            assign[p] = pd.Series([], dtype="object")
            rows[p] = pd.Series(0, index=names)

    counts = pd.DataFrame(rows).T[names]
    return counts, assign, snaps


def bleed_between(assign, p0, p1):
    """(customers Hyper-Active/Active at p0 who are At-Risk at p1, size of that source group)"""
    a0, a1 = assign[p0], assign[p1]
    src = set(a0[a0.isin(["Hyper-Active", "Active"])].index) if len(a0) else set()
    dst = set(a1[a1 == "At-Risk"].index) if len(a1) else set()
    return len(src & dst), len(src)


def stable_core(full_df, product, today):
    """Customers who ordered in Jan-Jun AND again in the last 30 days."""
    full = _product_orders(full_df, product, today)
    if full is None:
        return 0, 0
    h1 = set(full[full["_d"] <= pd.Timestamp("2026-06-30")]["_key"])
    recent = set(full[full["_d"] > today - timedelta(days=30)]["_key"])
    return len(h1 & recent), len(h1)


# ============================================================
# CHART — stacked bars + segment arrows + bleed arrows + MoM brackets
# ============================================================
def render_recency_chart(product, counts, assign, snaps, key):

    periods = list(counts.index)
    n = len(periods)
    xs = list(range(n))
    names = list(counts.columns)
    totals = counts.sum(axis=1)
    M = float(totals.max()) if n else 0
    if M == 0:
        st.info(f"No {product} orders in the period.")
        return

    shares = counts.div(totals.replace(0, np.nan), axis=0).fillna(0) * 100
    M = 100.0                       # every bar is drawn 100% tall
    half = 0.22
    snap_dates = dict(snaps)

    ticks = []
    for p in periods:
        mtd = snap_dates[p] < p.end_time.normalize()
        ticks.append(f"<b>{p.strftime('%b')}{' MTD' if mtd else ''}</b><br>{int(totals[p]):,}")

    bottoms, running = {}, pd.Series(0.0, index=counts.index)
    for bk in names:
        bottoms[bk] = running.copy()
        running = running + shares[bk]

    fig = go.Figure()
    annotations = []

    # ---------------- background phases ----------------
    for label, m0, m1, tint in PHASES:
        idx = [i for i, p in enumerate(periods) if m0 <= p.month <= m1]
        if not idx:
            continue
        x0 = -0.6 if idx[0] == 0 else idx[0] - 0.5
        x1 = n - 0.4 if idx[-1] == n - 1 else idx[-1] + 0.5
        fig.add_vrect(x0=x0, x1=x1, fillcolor=tint, line_width=0, layer="below")
        annotations.append(dict(
            x=(x0 + x1) / 2, y=M * 1.28, text=f"<b>{label}</b>", showarrow=False,
            font=dict(size=9, color="#444444"),
        ))

    # ---------------- stacked bars ----------------
    for bk in names:
        fill, txt = BUCKET_STYLE[bk]
        label = bucket_label(product, bk)
        text, hover = [], []
        for p in periods:
            v = int(counts.loc[p, bk])
            sh = shares.loc[p, bk]
            hover.append(f"{p.strftime('%b %Y')} · {label}<br>{v:,} customers "
                         f"({sh:.0f}% of {int(totals[p]):,})")
            text.append(f"{v:,}<br>({sh:.0f}%)" if sh >= 6 else "")
        fig.add_trace(go.Bar(
            x=xs, y=shares[bk].values, width=2 * half, name=label,
            marker=dict(color=fill, line=dict(color="white", width=1)),
            text=text, textposition="inside", insidetextanchor="middle",
            textfont=dict(size=8, color=txt),
            hovertext=hover, hovertemplate="%{hovertext}<extra></extra>",
        ))

    # ---------------- same-bucket arrows between neighbouring months ----------------
    rope = {UP_COLOR: ([], []), DOWN_COLOR: ([], []), FLAT_COLOR: ([], [])}
    for i in range(n - 1):
        a, b = periods[i], periods[i + 1]
        if b != a + 1:
            continue
        for bk in names:
            va, vb = float(counts.loc[a, bk]), float(counts.loc[b, bk])
            if va == 0:
                continue
            ya = bottoms[bk][a] + shares.loc[a, bk] / 2
            yb = bottoms[bk][b] + shares.loc[b, bk] / 2
            x0, x1 = xs[i] + half, xs[i + 1] - half
            ch = (vb - va) / va * 100
            c = change_colour(ch, bk)
            rope[c][0].extend([x0, x1, None])
            rope[c][1].extend([ya, yb, None])
            annotations.append(dict(
                x=x1, y=yb, ax=x1 - (x1 - x0) * 0.25, ay=yb - (yb - ya) * 0.25,
                xref="x", yref="y", axref="x", ayref="y", text="",
                showarrow=True, arrowhead=2, arrowsize=1.0, arrowwidth=1.4,
                arrowcolor=c,
            ))
            annotations.append(dict(
                x=(x0 + x1) / 2, y=(ya + yb) / 2, text=f"<b>{ch:+.0f}%</b>",
                showarrow=False, font=dict(size=8, color=c),
                bgcolor="rgba(255,255,255,0.9)", borderpad=1,
            ))
    for c, (lx, ly) in rope.items():
        if lx:
            fig.add_trace(go.Scatter(
                x=lx, y=ly, mode="lines", showlegend=False, hoverinfo="skip",
                line=dict(color=c, width=1.2, dash="dash"),
            ))

    # ---------------- cohort bleed: Hyper-Active/Active -> At-Risk ----------------
    for m0, m1 in BLEED_PAIRS:
        for i in range(n - 1):
            a, b = periods[i], periods[i + 1]
            if not (a.month == m0 and b.month == m1 and b == a + 1):
                continue
            flow, src_n = bleed_between(assign, a, b)
            if src_n == 0:
                continue
            ysrc = (shares.loc[a, "Hyper-Active"] + shares.loc[a, "Active"]) / 2
            ydst = bottoms["At-Risk"][b] + shares.loc[b, "At-Risk"] / 2
            x0, x1 = xs[i] + half, xs[i + 1] - half
            annotations.append(dict(
                x=x1, y=ydst, ax=x0, ay=ysrc,
                xref="x", yref="y", axref="x", ayref="y", text="",
                showarrow=True, arrowhead=3, arrowsize=1.4, arrowwidth=3.2,
                arrowcolor="#8b0000",
            ))
            annotations.append(dict(
                x=(x0 + x1) / 2, y=(ysrc + ydst) / 2,
                text=f"<b>BLEED {flow:,}</b><br>({flow / src_n * 100:.0f}% of active)",
                showarrow=False, font=dict(size=8, color="white"),
                bgcolor="#8b0000", borderpad=2,
            ))

    # ---------------- overall MoM brackets along the top ----------------
    bx, by = [], []
    y_top = M * 1.12
    for i in range(n - 1):
        a, b = periods[i], periods[i + 1]
        if b != a + 1:
            continue
        ta, tb = float(totals[a]), float(totals[b])
        if ta == 0:
            continue
        xa, xb = xs[i] + 0.08, xs[i + 1] - 0.08
        bx += [xa, xa, xb, None]
        by += [M * 1.02, y_top, y_top, None]
        ch = (tb - ta) / ta * 100
        c = change_colour(ch)
        annotations.append(dict(
            x=xb, y=M * 1.02, ax=xb, ay=y_top,
            xref="x", yref="y", axref="x", ayref="y", text="",
            showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=1.8,
            arrowcolor=c,
        ))
        annotations.append(dict(
            x=(xa + xb) / 2, y=y_top, text=f"<b>{ch:+.1f}%</b>", showarrow=False,
            font=dict(size=9, color=c), bgcolor="white",
            bordercolor=c, borderwidth=1, borderpad=2,
        ))
    if bx:
        fig.add_trace(go.Scatter(
            x=bx, y=by, mode="lines", showlegend=False, hoverinfo="skip",
            line=dict(color="#001f6e", width=1.6),
        ))

    fig.update_layout(
        barmode="stack", bargap=0,
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(tickmode="array", tickvals=xs, ticktext=ticks,
                   range=[-0.6, n - 0.4], showgrid=False, title="",
                   tickfont=dict(size=10, color="#222222")),
        yaxis=dict(title="Share of base", range=[0, M * 1.34],
                   tickvals=[0, 25, 50, 75, 100], ticksuffix="%",
                   showgrid=True, gridcolor="#f0f0f0", zeroline=False),
        legend=dict(orientation="h", yanchor="top", y=-0.12,
                    xanchor="center", x=0.5, font=dict(size=10)),
        annotations=annotations,
        height=640,
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


# ============================================================
# INSIGHTS HEADER (numbers come from the data)
# ============================================================
def _recency_insight_lines(product, result, full_df, today):
    counts, assign, snaps = result
    totals = counts.sum(axis=1)
    peak_p, peak = totals.idxmax(), int(totals.max())
    last_p, last = counts.index[-1], int(totals.iloc[-1])
    chg = (last - peak) / peak * 100 if peak else 0
    ar_peak = int(counts.loc[peak_p, "At-Risk"])
    ar_last = int(counts.loc[last_p, "At-Risk"])
    core_n, h1_n = stable_core(full_df, product, today)

    parts = [
        f"<b>{product}:</b> the base peaked at <b>{peak:,}</b> customers in "
        f"{peak_p.strftime('%b')} and is <b>{last:,}</b> now "
        f"({last_p.strftime('%b')}), a change of <b>{chg:+.0f}%</b>. "
        f"At-Risk grew from {ar_peak:,} at the peak to {ar_last:,} "
        f"({ar_last / last * 100 if last else 0:.0f}% of today's base)."
    ]

    jul, aug, sep = (pd.Period("2026-07", "M"), pd.Period("2026-08", "M"),
                     pd.Period("2026-09", "M"))
    if jul in assign and aug in assign:
        f1, s1 = bleed_between(assign, jul, aug)
        txt = f"{f1:,} of {s1:,} July Hyper-Active/Active customers were At-Risk by August"
        if sep in assign:
            f2, s2 = bleed_between(assign, aug, sep)
            txt += f"; {f2:,} of {s2:,} August Hyper-Active/Active customers were At-Risk by September"
        parts.append(txt + ".")

    if h1_n:
        parts.append(
            f"Stable core: <b>{core_n:,}</b> of the {h1_n:,} customers who "
            f"ordered in Jan–Jun ({core_n / h1_n * 100:.0f}%) have ordered again "
            f"in the last 30 days."
        )
    return " ".join(parts)


def render_recency_header(results, full_df, today):
    items = ""
    for product in ["Petrol", "Gas"]:
        if results.get(product) is None:
            continue
        items += ("<li style='margin-bottom:6px;'>"
                  + _recency_insight_lines(product, results[product], full_df, today)
                  + "</li>")
    html = (
        "<div style='background:white;border-left:6px solid #003399;"
        "border-radius:12px;padding:16px 22px;margin-bottom:18px;"
        "box-shadow:0 4px 12px rgba(0,51,153,0.10);'>"
        "<div style='color:#003399;font-size:13px;font-weight:800;"
        "text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;'>"
        "Insights: seasonal university departures vs the year-round core</div>"
        f"<ul style='margin:0 0 8px 18px;padding:0;color:#222;font-size:13px;line-height:1.55;'>{items}</ul>"
        "<div style='color:#555;font-size:12px;line-height:1.5;'>"
        "<b>Reading it:</b> the July surge followed by the August–September "
        "bleed of Hyper-Active/Active customers into At-Risk fits students and "
        "temporary residents leaving for the university break. The customers "
        "who keep ordering through the break (the stable core above) are the "
        "year-round town residents. The data does not record who is a student, "
        "so this is an inference from timing, not a tagged fact."
        "</div></div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def _bleed_table(result):
    counts, assign, snaps = result
    rows = []
    periods = list(counts.index)
    for i in range(len(periods) - 1):
        a, b = periods[i], periods[i + 1]
        flow, src_n = bleed_between(assign, a, b)
        rows.append({
            "Month pair": f"{a.strftime('%b')} → {b.strftime('%b')}",
            "Hyper-Active + Active (first month)": src_n,
            "At-Risk the next month": flow,
            "Bleed %": f"{flow / src_n * 100:.0f}%" if src_n else "",
        })
    return pd.DataFrame(rows).set_index("Month pair")


# ============================================================
# RETENTION SECTION (keeps the same function name used by app.py)
#   orders_df       = filtered orders (only used for the New vs Returning tables)
#   full_orders_df  = ALL orders, unfiltered (used for the Active Base charts)
# ============================================================
def render_retention_cohort(orders_df, full_orders_df=None):

    st.markdown("<br>", unsafe_allow_html=True)

    if full_orders_df is None:
        st.warning(
            "Full (unfiltered) order history was not supplied, so results are "
            "built from filtered data. Pass full_orders_df=<all orders> for "
            "correct results."
        )
        full_orders_df = orders_df

    today = pd.Timestamp.now().normalize()

    # ================= ACTIVE BASE MOVEMENT =================
    st.markdown(
        "<div class='section-title'>🔄 Active Base Movement — Petrol & Gas</div>",
        unsafe_allow_html=True
    )

    results = {p: build_recency(full_orders_df, p, today) for p in ["Petrol", "Gas"]}

    if all(r is None for r in results.values()):
        st.info("No Petrol or Gas orders found from 1 Jan 2026 to today.")
    else:
        render_recency_header(results, full_orders_df, today)

        window = (f"the last {LOOKBACK_DAYS} days" if LOOKBACK_DAYS
                  else "all time")
        chart_note(
            "Each bar is the customer base at the end of that month (current "
            "month = month to date), covering 1 Jan 2026 to today. Every bar is "
            "scaled to 100% so the mix is easy to compare; the number under the "
            "month is the real customer count and hovering a segment shows its "
            "count. The base = "
            f"customers who ordered that product in {window}, split by days "
            "since their last order of that product. Petrol and Gas use different recency "
            "windows because their buying cycles differ (see the legend). "
            "Arrows between bars show the % change of each bucket (green = "
            "healthier, red = worse; for At-Risk an increase is red). The "
            "bracket on top shows the month-over-month change of the whole "
            "base. Thick dark-red arrows show the bleed: Hyper-Active/Active "
            "customers in July who were At-Risk the next month, and August to "
            "September. Jan–Mar are understated in the older buckets because "
            "order data starts on 1 Jan. Only Petrol and Gas orders are "
            "counted; customers are matched by name."
        )

        if SIDE_BY_SIDE:
            cols = st.columns(2)
        else:
            cols = [st.container(), st.container()]

        for col, product in zip(cols, ["Petrol", "Gas"]):
            with col:
                st.markdown(
                    f"<div class='section-title'>{'⛽' if product == 'Petrol' else '🔥'} "
                    f"{product} Active Base</div>",
                    unsafe_allow_html=True
                )
                if results[product] is None:
                    st.info(f"No {product} orders in the period.")
                else:
                    counts, assign, snaps = results[product]
                    render_recency_chart(product, counts, assign, snaps,
                                         key=f"recency_{product.lower()}")

        st.markdown(
            "<div class='section-title'>📋 Bleed Table — Hyper-Active/Active → At-Risk, month to month</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "For each pair of months: how many customers were Hyper-Active or "
            "Active at the end of the first month and had slipped to At-Risk by "
            "the end of the next."
        )
        tcols = st.columns(2) if SIDE_BY_SIDE else [st.container(), st.container()]
        for col, product in zip(tcols, ["Petrol", "Gas"]):
            with col:
                st.markdown(f"**{product}**")
                if results[product] is not None:
                    st.dataframe(_bleed_table(results[product]),
                                 use_container_width=True)

    # ================= NEW vs RETURNING =================
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-title'>👥 Customers Per Month: New vs Returning</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "New = first-ever order that month. "
        "Returning = ordered this month but first ordered in an earlier month. "
        "Total Active = New + Returning, and matches the Active count on the "
        "Customer tab."
    )
    m_summary = new_vs_returning_summary(full_orders_df, orders_df, "M")
    if m_summary is not None and not m_summary.empty:
        st.dataframe(m_summary, use_container_width=True)
    else:
        st.info("No data for the selected period.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-title'>👥 Customers Per Week: New vs Returning</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "Same split by week: New = first-ever order that week, "
        "Returning = ordered before. Shows the latest 12 weeks in the "
        "selected period."
    )
    w_summary = new_vs_returning_summary(full_orders_df, orders_df, "W")
    if w_summary is not None and not w_summary.empty:
        st.dataframe(w_summary.tail(12), use_container_width=True)
    else:
        st.info("No weekly data for the selected period.")
    st.markdown("<br>", unsafe_allow_html=True)


# ============================================================
# PRODUCT FREQUENCY DEEP DIVE
# Lifetime stats (days since last order, avg gap between orders)
# use the full order history so the filter cannot distort them.
# ============================================================
def render_product_frequency(orders_df, full_orders_df=None):

    today = pd.Timestamp.now().normalize()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-title'>⏱️ Product Frequency Deep Dive</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "How frequently customers reorder, calculated from each customer's "
        "complete order history. "
        "Avg Days Between Orders = how long the typical customer waits before reordering. "
        "Lower = more engaged customers. Higher = customers are spacing out orders "
        "or buying from competitors between GasFeel orders."
    )

    source = full_orders_df if full_orders_df is not None else orders_df
    source = add_customer_key(source)

    customer_orders = source.sort_values(
        ["_key", "Date of Order"]
    ).groupby("_key").agg(
        **{"Customer Name": ("Customer Name", "last")},
        Total_Orders=("Order ID", "count"),
        First_Order=("Date of Order", "min"),
        Last_Order=("Date of Order", "max"),
        Total_Revenue=("Revenue", "sum"),
        Products=("Order Type",
                  lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else "Unknown")
    ).reset_index()

    customer_orders["Days Since Last Order"] = (
        today - customer_orders["Last_Order"]
    ).dt.days
    customer_orders["Tenure Days"] = (
        customer_orders["Last_Order"] - customer_orders["First_Order"]
    ).dt.days
    customer_orders["Avg Days Between Orders"] = (
        customer_orders["Tenure Days"] /
        (customer_orders["Total_Orders"] - 1)
    ).where(customer_orders["Total_Orders"] > 1, None).round(1)

    early_risk = customer_orders[
        (customer_orders["Days Since Last Order"] >= 14) &
        (customer_orders["Days Since Last Order"] < 30)
    ].sort_values("Days Since Last Order", ascending=False)

    col1, col2, col3 = st.columns(3)

    avg_days = customer_orders[
        customer_orders["Avg Days Between Orders"].notna()
    ]["Avg Days Between Orders"].mean()

    with col1:
        st.metric(
            label="Avg Days Between Orders",
            value=f"{avg_days:.1f} days" if pd.notna(avg_days) else "N/A"
        )
    with col2:
        st.metric(
            label="Early At-Risk (14-30 days)",
            value=str(len(early_risk)),
            delta=f"-{len(early_risk)} need attention",
            delta_color="inverse"
        )
    with col3:
        repeat = customer_orders[customer_orders["Total_Orders"] > 1]
        st.metric(
            label="Repeat Customers",
            value=f"{len(repeat):,}",
            delta=f"{(len(repeat)/len(customer_orders)*100):.1f}% of base"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ---------------- Early At-Risk table ----------------
    if not early_risk.empty:
        st.markdown(
            "<div class='section-title'>⚠️ Early At-Risk Customers (14-30 Days Silent)</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Customers who have not ordered in 14-30 days. "
            "They are not yet in the official 'At Risk' category (30 days) "
            "but are showing early signs of disengagement. "
            "A proactive call now is much easier than a re-engagement "
            "campaign after they have fully churned."
        )
        early_display = early_risk[[
            "Customer Name", "Days Since Last Order",
            "Total_Orders", "Total_Revenue", "Products"
        ]].copy()
        early_display["Total_Revenue"] = early_display["Total_Revenue"].apply(format_naira)
        early_display = early_display.rename(columns={
            "Customer Name":         "Customer",
            "Days Since Last Order": "Days Silent",
            "Total_Orders":          "Total Orders",
            "Total_Revenue":         "Total Revenue",
            "Products":              "Main Product"
        })
        st.dataframe(early_display, width="stretch", hide_index=True, height=280)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---------------- Most / least frequent ----------------
    col4, col5 = st.columns(2)
    freq_customers = customer_orders[
        customer_orders["Avg Days Between Orders"].notna()
    ].copy()

    freq_cols = ["Customer Name", "Avg Days Between Orders",
                 "Total_Orders", "Total_Revenue"]
    freq_rename = {
        "Customer Name": "Customer",
        "Total_Orders":  "Orders",
        "Total_Revenue": "Revenue"
    }

    with col4:
        st.markdown(
            "<div class='section-title'>🏆 Most Frequent Customers</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Customers with the shortest average time between orders. "
            "These are your most loyal and engaged customers. "
            "They deserve priority service, loyalty rewards, "
            "and first access to promotions."
        )
        top_freq = freq_customers.nsmallest(10, "Avg Days Between Orders")[freq_cols].copy()
        top_freq["Total_Revenue"] = top_freq["Total_Revenue"].apply(format_naira)
        st.dataframe(top_freq.rename(columns=freq_rename),
                     width="stretch", hide_index=True)

    with col5:
        st.markdown(
            "<div class='section-title'>📉 Least Frequent Customers</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Customers with the longest average gap between orders. "
            "They may be using GasFeel only occasionally or "
            "splitting orders between GasFeel and competitors. "
            "Target these customers with frequency incentives — "
            "discounts for ordering twice in one week for example."
        )
        bottom_freq = freq_customers.nlargest(10, "Avg Days Between Orders")[freq_cols].copy()
        bottom_freq["Total_Revenue"] = bottom_freq["Total_Revenue"].apply(format_naira)
        st.dataframe(bottom_freq.rename(columns=freq_rename),
                     width="stretch", hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---------------- Order frequency distribution ----------------
    st.markdown(
        "<div class='section-title'>📊 Order Frequency Distribution</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "How many customers have placed 1, 2, 3, 4+ orders in total. "
        "A tall bar at 1 means most customers only ordered once — "
        "a retention problem. Growing bars at 3, 4, 5+ means "
        "customers are becoming loyal repeat buyers."
    )

    freq_dist = customer_orders["Total_Orders"].value_counts().reset_index()
    freq_dist.columns = ["Orders Count", "Customers"]
    freq_dist = freq_dist.sort_values("Orders Count")

    fig_dist = px.bar(
        freq_dist, x="Orders Count", y="Customers", text="Customers",
        color_discrete_sequence=["#003399"]
    )
    fig_dist.update_traces(
        textposition="outside", textfont=dict(size=10, color="#333333")
    )
    fig_dist.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=5, r=5, t=10, b=5),
        xaxis=dict(showgrid=False, title="Number of Orders", tickmode="linear"),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title="Number of Customers"),
        height=300
    )
    st.plotly_chart(fig_dist, width="stretch")