# ============================================================
# SALES TRACKER TAB — GasFeel Dashboard
# Shows Yesterday, WTD, MTD, YTD KPIs, Summary Metrics,
# and Revenue Trend chart.
# ============================================================

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import timedelta


# ============================================================
# HELPER — FORMAT NAIRA VALUES
# ============================================================
def format_naira(value):
    try:
        if pd.isna(value) or value == 0:
            return "₦0"
    except:
        return "₦0"
    if value >= 1_000_000:
        return f"₦{value/1_000_000:.2f}M"
    elif value >= 1_000:
        return f"₦{value/1_000:.2f}K"
    else:
        return f"₦{value:,.0f}"


# ============================================================
# HELPER — PLAIN KPI CARD (no indicator)
# ============================================================
def kpi_card(label, value):
    st.metric(label=label, value=value, delta=None)


# ============================================================
# HELPER — INDICATOR CARD
# Shows main amount as value and coloured % as delta
# ============================================================
def indicator_card(label, amount, indicator, indicator_color="green"):
    raw = indicator.replace("▲","").replace("▼","").replace("%","").strip()
    try:
        num = float(raw)
        delta_val = num if indicator_color == "green" else -num
    except:
        delta_val = 0
    st.metric(
        label=label,
        value=amount,
        delta=f"{delta_val:.1f}%",
        delta_color="normal"
    )


# ============================================================
# HELPER — VS CALCULATION
# Returns arrow string, color, and formatted actual amount
# ============================================================
def calc_vs(actual, compare):
    if compare == 0:
        return "N/A", "green"
    pct = ((actual - compare) / compare) * 100
    arrow = f"▲{abs(pct):.1f}%" if pct >= 0 else f"▼{abs(pct):.1f}%"
    color = "green" if pct >= 0 else "red"
    return arrow, color


# ============================================================
# MAIN RENDER FUNCTION — SALES TRACKER
# ============================================================
def render_sales_tracker(df, targets):

    # --------------------------------------------------------
    # STEP 1 — DATE BOUNDARIES
    # --------------------------------------------------------
    today = pd.Timestamp.now().normalize()
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    # --------------------------------------------------------
    # STEP 2 — FILTER DATA INTO TIME PERIODS
    # --------------------------------------------------------
    df_y   = df[df["Date of Order"].dt.normalize() == yesterday]
    df_wtd = df[df["Date of Order"].dt.normalize() >= week_start]
    df_mtd = df[df["Date of Order"].dt.normalize() >= month_start]
    df_ytd = df[df["Date of Order"].dt.normalize() >= year_start]

    # --------------------------------------------------------
    # STEP 3 — CALCULATE KPIs PER PERIOD
    # GMV = Total Customer Payment
    # Revenue = GMV - COGS
    # Profit = Revenue - Delivery Cost
    # --------------------------------------------------------
    def calc(d):
        return {
            "gmv":       d["GMV"].sum(),
            "revenue":   d["Revenue"].sum(),
            "orders":    len(d),
            "profit":    d["Profit"].sum(),
            "break_even": d["COGS(naira)"].sum() + d[
                "Delivery Cost (how much we paid to the Rider)"
            ].sum()
        }

    y   = calc(df_y)
    wtd = calc(df_wtd)
    mtd = calc(df_mtd)
    ytd = calc(df_ytd)

    # --------------------------------------------------------
    # STEP 4 — SUMMARY METRICS (full filtered dataset)
    # --------------------------------------------------------
    total_gmv    = df["GMV"].sum()
    total_rev    = df["Revenue"].sum()
    total_profit = df["Profit"].sum()
    total_orders = len(df)
    rev_margin   = (total_rev / total_gmv * 100) if total_gmv > 0 else 0
    profit_margin = (total_profit / total_rev * 100) if total_rev > 0 else 0
    avg_daily    = total_rev / max(df["Date of Order"].nunique(), 1)
    active       = df[
        df["Date of Order"].dt.normalize() >= today - timedelta(days=30)
    ]["Customer Name"].nunique()
    counts       = df.groupby("Customer Name")["Order ID"].count()
    repeat_rate  = (counts > 1).sum() / counts.count() * 100 if counts.count() > 0 else 0

    # --------------------------------------------------------
    # STEP 5 — TARGET LOOKUPS
    # Sum daily targets across each time window
    # --------------------------------------------------------
    def get_target(start, end, col):
        mask = (
            (targets["Period Type"] == "Daily") &
            (targets["Period"] >= start) &
            (targets["Period"] <= end)
        )
        return targets[mask][col].sum()

    t_wtd = get_target(week_start, today, "Target GMV")
    t_mtd = get_target(month_start, today, "Target GMV")
    t_ytd = get_target(year_start, today, "Target GMV")

    # --------------------------------------------------------
    # STEP 6 — VS LAST WEEK
    # lw_revenue = actual revenue from same days last week
    # t_wtd_revenue = sum of daily Target Revenue this week
    # --------------------------------------------------------
    lw_start   = week_start - timedelta(days=7)
    lw_end     = today - timedelta(days=7)
    lw_revenue = df[
        (df["Date of Order"].dt.normalize() >= lw_start) &
        (df["Date of Order"].dt.normalize() <= lw_end)
    ]["Revenue"].sum()

    t_wtd_revenue = targets[
        (targets["Period Type"] == "Daily") &
        (targets["Period"] >= week_start) &
        (targets["Period"] <= today)
    ]["Target Revenue"].sum()

    # --------------------------------------------------------
    # STEP 7 — VS LAST MONTH
    # lm_revenue = actual revenue from same days last month
    # t_mtd_revenue = sum of daily Target Revenue this month
    # --------------------------------------------------------
    days_in    = (today - month_start).days
    lm_start   = (month_start - timedelta(days=1)).replace(day=1)
    lm_end     = lm_start + timedelta(days=days_in)
    lm_revenue = df[
        (df["Date of Order"].dt.normalize() >= lm_start) &
        (df["Date of Order"].dt.normalize() <= lm_end)
    ]["Revenue"].sum()

    t_mtd_revenue = targets[
        (targets["Period Type"] == "Daily") &
        (targets["Period"] >= month_start) &
        (targets["Period"] <= today)
    ]["Target Revenue"].sum()

    # --------------------------------------------------------
    # STEP 8 — YTD TARGET REVENUE
    # t_ytd_revenue = sum of daily Target Revenue Jan 1 to today
    # --------------------------------------------------------
    t_ytd_revenue = targets[
        (targets["Period Type"] == "Daily") &
        (targets["Period"] >= year_start) &
        (targets["Period"] <= today)
    ]["Target Revenue"].sum()

    # --------------------------------------------------------
    # STEP 9 — YTD STATUS based on Revenue vs Target
    # --------------------------------------------------------
    if t_ytd_revenue > 0:
        pct_ytd    = ytd["revenue"] / t_ytd_revenue
        ytd_status = "🟢 Ahead" if pct_ytd >= 1.0 else (
                     "🟡 On Track" if pct_ytd >= 0.8 else "🔴 At Risk")
    else:
        ytd_status = "⚪ No Target"

    # --------------------------------------------------------
    # STEP 10 — REVENUE TREND for line chart
    # --------------------------------------------------------
    trend = df.groupby(["Year", "Month", "Month Name"])[
        "Revenue"
    ].sum().reset_index().sort_values(["Year", "Month"])
    trend["Label"] = trend.apply(
        lambda r: pd.Timestamp(
            year=int(r["Year"]), month=int(r["Month"]), day=1
        ).strftime("%b %Y"), axis=1
    )

    # ========================================================
    # LAYOUT
    # ========================================================
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("<div class='section-title'>📅 Yesterday Sales</div>", unsafe_allow_html=True)
        kpi_card("GMV",        format_naira(y["gmv"]))
        kpi_card("Revenue",    format_naira(y["revenue"]))
        kpi_card("Orders",     str(y["orders"]))
        kpi_card("Profit",     format_naira(y["profit"]))
        kpi_card("Break-Even", format_naira(y["break_even"]))

    with c2:
        st.markdown("<div class='section-title'>📆 WTD Sales</div>", unsafe_allow_html=True)
        kpi_card("GMV",     format_naira(wtd["gmv"]))
        kpi_card("Revenue", format_naira(wtd["revenue"]))
        kpi_card("Orders",  str(wtd["orders"]))

        # Vs Last Week — last week's actual revenue + % change indicator
        pct_lw = ((wtd["revenue"] - lw_revenue) / lw_revenue * 100) if lw_revenue > 0 else 0
        arrow_lw = f"▲{abs(pct_lw):.1f}%" if pct_lw >= 0 else f"▼{abs(pct_lw):.1f}%"
        color_lw = "green" if pct_lw >= 0 else "red"
        indicator_card("Vs Last Week", format_naira(lw_revenue), arrow_lw, color_lw)

        # Vs Target — this week's target revenue + % achievement indicator
        pct_wtd = ((wtd["revenue"] - t_wtd_revenue) / t_wtd_revenue * 100) if t_wtd_revenue > 0 else 0
        arrow_wtd = f"▲{abs(pct_wtd):.1f}%" if pct_wtd >= 0 else f"▼{abs(pct_wtd):.1f}%"
        color_wtd = "green" if pct_wtd >= 0 else "red"
        indicator_card("Vs Target Revenue", format_naira(t_wtd_revenue), arrow_wtd, color_wtd)

    with c3:
        st.markdown("<div class='section-title'>📊 Summary Metrics</div>", unsafe_allow_html=True)
        rm_delta = rev_margin if rev_margin >= 0 else -abs(rev_margin)
        st.metric("Revenue Margin", f"{rev_margin:.1f}%",
                  delta=f"{rm_delta:.1f}%", delta_color="normal")
        pm_delta = profit_margin if profit_margin >= 0 else -abs(profit_margin)
        st.metric("Profit Margin", f"{profit_margin:.1f}%",
                  delta=f"{pm_delta:.1f}%", delta_color="normal")
        kpi_card("Avg Daily Revenue", format_naira(avg_daily))
        kpi_card("Total Orders",      str(total_orders))
        kpi_card("Active Customers",  str(active))
        st.metric("Repeat Rate", f"{repeat_rate:.1f}%",
                  delta=f"{repeat_rate:.1f}%", delta_color="normal")

    st.markdown("<br>", unsafe_allow_html=True)

    c4, c5, c6 = st.columns([1, 1, 1.5])

    with c4:
        st.markdown("<div class='section-title'>🗓️ MTD Sales</div>", unsafe_allow_html=True)
        kpi_card("GMV",     format_naira(mtd["gmv"]))
        kpi_card("Revenue", format_naira(mtd["revenue"]))
        kpi_card("Orders",  str(mtd["orders"]))

        # Vs Last Month — last month's actual revenue + % change indicator
        pct_lm = ((mtd["revenue"] - lm_revenue) / lm_revenue * 100) if lm_revenue > 0 else 0
        arrow_lm = f"▲{abs(pct_lm):.1f}%" if pct_lm >= 0 else f"▼{abs(pct_lm):.1f}%"
        color_lm = "green" if pct_lm >= 0 else "red"
        indicator_card("Vs Last Month", format_naira(lm_revenue), arrow_lm, color_lm)

        # Vs Target — this month's target revenue + % achievement indicator
        pct_mtd = ((mtd["revenue"] - t_mtd_revenue) / t_mtd_revenue * 100) if t_mtd_revenue > 0 else 0
        arrow_mtd = f"▲{abs(pct_mtd):.1f}%" if pct_mtd >= 0 else f"▼{abs(pct_mtd):.1f}%"
        color_mtd = "green" if pct_mtd >= 0 else "red"
        indicator_card("Vs Target Revenue", format_naira(t_mtd_revenue), arrow_mtd, color_mtd)

    with c5:
        st.markdown("<div class='section-title'>📈 YTD Sales</div>", unsafe_allow_html=True)
        kpi_card("GMV",     format_naira(ytd["gmv"]))
        kpi_card("Revenue", format_naira(ytd["revenue"]))
        kpi_card("Orders",  str(ytd["orders"]))
        kpi_card("Status",  ytd_status)

        # Vs Target — YTD target revenue + % achievement indicator
        pct_ytd_rev = ((ytd["revenue"] - t_ytd_revenue) / t_ytd_revenue * 100) if t_ytd_revenue > 0 else 0
        arrow_ytd = f"▲{abs(pct_ytd_rev):.1f}%" if pct_ytd_rev >= 0 else f"▼{abs(pct_ytd_rev):.1f}%"
        color_ytd = "green" if pct_ytd_rev >= 0 else "red"
        indicator_card("Vs Target Revenue", format_naira(t_ytd_revenue), arrow_ytd, color_ytd)

    with c6:
        st.markdown("<div class='section-title'>📉 Revenue Trend</div>", unsafe_allow_html=True)
        if not trend.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=trend["Label"],
                y=trend["Revenue"],
                mode="lines+markers+text",
                line=dict(color="#003399", width=3),
                marker=dict(color="#003399", size=9),
                text=trend["Revenue"].apply(format_naira),
                textposition="top center",
                textfont=dict(size=11, color="#333333")
            ))
            fig.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=10, r=20, t=20, b=10),
                xaxis=dict(showgrid=False, title="",
                           tickfont=dict(color="#333333")),
                yaxis=dict(showgrid=True, gridcolor="#f0f0f0",
                           title="", tickfont=dict(color="#333333")),
                showlegend=False, height=300
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available for revenue trend.")