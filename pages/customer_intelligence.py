# ============================================================
# CUSTOMER INTELLIGENCE TAB — GasFeel Dashboard
# Snapshot KPIs, run-out and reachout lists, membership,
# acquisition, deposits, New vs Returning, active-base retention
# (monthly + weekly) and product frequency.
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
# ACTIVE-BASE RETENTION ENGINE
# Base for each period = ALL customers who ordered in that period
# (new + returning). Retention in period +N = how many of those same
# customers ordered again N periods later.
#
# Returns:
#   counts — rows = period, cols = 0..max_periods
#            NaN = period has not happened yet, 0 = nobody came back
#   new    — Series: how many of the base were new in that period
# ============================================================
def build_active_base(full_df, view_df, freq, max_periods):

    full = add_customer_key(full_df)
    if full.empty:
        return None, None

    full["_period"] = full["Date of Order"].dt.to_period(freq)

    first_period = full.groupby("_key")["_period"].min()
    new_by_period = first_period.value_counts()
    active_sets = full.groupby("_period")["_key"].apply(set).to_dict()

    all_periods = pd.period_range(
        full["_period"].min(), full["_period"].max(), freq=freq
    )
    current_period = pd.Timestamp.now().to_period(freq)

    rows = {}
    for p in all_periods:
        base = active_sets.get(p, set())
        row = {}
        for n in range(0, max_periods + 1):
            target = p + n
            if target > current_period:
                row[n] = float("nan")              # not happened yet
            elif n == 0:
                row[n] = len(base)
            else:
                row[n] = len(base & active_sets.get(target, set()))
        rows[p] = row

    counts = pd.DataFrame.from_dict(rows, orient="index")
    new = new_by_period.reindex(counts.index).fillna(0).astype(int)

    # Filter only decides which periods are displayed
    view = pd.to_datetime(view_df["Date of Order"], errors="coerce").dropna()
    if not view.empty:
        shown = view.dt.to_period(freq).unique()
        counts = counts[counts.index.isin(shown)]

    counts = counts[counts[0] > 0]
    new = new.loc[counts.index]

    if counts.empty:
        return None, None
    return counts, new


# ============================================================
# RETENTION DISPLAY (shared by monthly and weekly)
# ============================================================
def render_active_views(counts, new, unit, zero_label, heat_height, key):

    sizes = counts[0].astype(int)
    pct   = counts.divide(sizes, axis=0) * 100
    cols  = list(counts.columns)

    def col_name(p):
        return zero_label if p == 0 else f"{unit} +{int(p)}"

    # ---------------- TABLE ----------------
    rows = []
    for period in counts.index:
        base = int(sizes[period])
        row = {
            "Period": str(period),
            "Total Active (Base)": base,
            "New": int(new[period]),
            "Returning": base - int(new[period]),
        }
        for p in cols:
            c = counts.loc[period, p]
            if pd.isna(c):
                row[col_name(p)] = ""
            elif p == 0:
                row[col_name(p)] = f"{int(c)} (100%)"
            else:
                row[col_name(p)] = f"{int(c)}/{base} ({pct.loc[period, p]:.0f}%)"
        rows.append(row)

    # Weighted average — only periods old enough to reach that column
    avg_row = {
        "Period": "WEIGHTED AVG",
        "Total Active (Base)": int(sizes.sum()),
        "New": int(new.sum()),
        "Returning": int(sizes.sum() - new.sum()),
    }
    for p in cols:
        eligible = counts[p].notna()
        if p == 0:
            avg_row[col_name(p)] = "100%"
        elif eligible.any() and sizes[eligible].sum() > 0:
            avg = counts.loc[eligible, p].sum() / sizes[eligible].sum() * 100
            avg_row[col_name(p)] = f"{avg:.0f}%"
        else:
            avg_row[col_name(p)] = ""
    rows.append(avg_row)

    st.dataframe(pd.DataFrame(rows).set_index("Period"), use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # ---------------- HEATMAP ----------------
    labels, hover = [], []
    for period in counts.index:
        base = int(sizes[period])
        r_lab, r_hov = [], []
        for p in cols:
            c = counts.loc[period, p]
            if pd.isna(c):
                r_lab.append("")
                r_hov.append("Not enough time has passed yet")
            else:
                r_lab.append(f"{int(c)}<br>({pct.loc[period, p]:.0f}%)")
                r_hov.append(
                    f"{int(c)} of {base} active customers "
                    f"({pct.loc[period, p]:.0f}%)"
                )
        labels.append(r_lab)
        hover.append(r_hov)

    fig = go.Figure(data=go.Heatmap(
        z=pct.values,
        x=[col_name(p) for p in cols],
        y=[f"{p}  (n={int(sizes[p])})" for p in counts.index],
        colorscale=[
            [0,   "#fff0f0"],
            [0.3, "#ccd9ff"],
            [0.6, "#8fb0ff"],
            [1,   "#4d79d9"],
        ],
        zmin=0, zmax=100,
        text=labels,
        texttemplate="%{text}",
        textfont=dict(size=10, color="#111111"),
        hovertext=hover,
        hovertemplate="%{y}<br>%{x}<br>%{hovertext}<extra></extra>",
        showscale=True,
        xgap=2, ygap=2,
    ))
    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis=dict(title=f"{unit}s after the active {unit.lower()}", side="top"),
        yaxis=dict(title="Active period (n = total active customers)",
                   autorange="reversed"),
        height=heat_height,
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


# ============================================================
# RETENTION ANALYSIS
# orders_df       = filtered orders (decides which periods are shown)
# full_orders_df  = ALL orders, unfiltered (decides who is active)
# ============================================================
def render_retention_cohort(orders_df, full_orders_df=None):

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-title'>🔄 Retention Analysis (Active Base)</div>",
        unsafe_allow_html=True
    )

    if full_orders_df is None:
        st.warning(
            "Full (unfiltered) order history was not supplied, so results are "
            "built from filtered data. Pass full_orders_df=<all orders> for "
            "correct results."
        )
        full_orders_df = orders_df

    chart_note(
        "Total Active (Base) = every customer who ordered in that month or week, "
        "split into New (first ever order in that period) and Returning "
        "(ordered before). Month +1, +2... show how many of THOSE SAME customers "
        "ordered again 1, 2... periods later. "
        "Example: '45/84 (54%)' = 45 of the 84 customers active in that month "
        "ordered again the next month. The base matches the Active count on the "
        "Customer tab and never changes with the filter. "
        "A blank cell means that period has not happened yet; '0 (0%)' means it "
        "has and nobody came back. WEIGHTED AVG = overall retention per column "
        "across all rows shown."
    )

    # ================= MONTHLY =================
    st.markdown(
        "<div class='section-title'>👥 Customers Per Month: New vs Returning</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "New = first-ever order that month. "
        "Returning = ordered this month but first ordered in an earlier month. "
        "Total Active = New + Returning. This is the base for the retention "
        "table below."
    )
    m_summary = new_vs_returning_summary(full_orders_df, orders_df, "M")
    if m_summary is not None and not m_summary.empty:
        st.dataframe(m_summary, use_container_width=True)
    else:
        st.info("No data for the selected period.")
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        "<div class='section-title'>📋 Month-on-Month Retention Table</div>",
        unsafe_allow_html=True
    )
    m_counts, m_new = build_active_base(full_orders_df, orders_df, "M", max_periods=12)

    if m_counts is None:
        st.info("No data for the selected period.")
    else:
        render_active_views(
            m_counts, m_new, unit="Month", zero_label="Month 0 (Active)",
            heat_height=max(320, 60 + 42 * len(m_counts)),
            key="monthly_active_heat"
        )

    # ================= WEEKLY =================
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

    st.markdown(
        "<div class='section-title'>📅 Week-by-Week Retention Table</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "Same logic by week. Each row = a week, with Total Active (Base) = "
        "every customer who ordered that week (New + Returning). Columns show "
        "how many of them ordered again in Week +1, +2 ... +8. "
        "Shows the latest 12 weeks in the selected period."
    )

    w_counts, w_new = build_active_base(full_orders_df, orders_df, "W", max_periods=8)

    if w_counts is None:
        st.info("No weekly data for the selected period.")
    else:
        w_counts = w_counts.tail(12)
        w_new = w_new.loc[w_counts.index]
        render_active_views(
            w_counts, w_new, unit="Week", zero_label="Week 0 (Active)",
            heat_height=max(320, 60 + 42 * len(w_counts)),
            key="weekly_active_heat"
        )


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