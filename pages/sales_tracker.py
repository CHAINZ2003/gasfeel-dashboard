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
# Converts numbers to readable Naira format
# ============================================================
def format_naira(value):
    if value >= 1_000_000:
        return f"₦{value/1_000_000:.2f}M"
    elif value >= 1_000:
        return f"₦{value/1_000:.2f}K"
    else:
        return f"₦{value:,.0f}"


# ============================================================
# HELPER — KPI CARD
# Shows label, main value, and optional coloured indicator.
# Uses st.metric for reliable green/red colouring.
# ============================================================
def kpi_card(label, value, indicator=None, indicator_color="green"):
    if indicator:
        raw = indicator.replace("▲","").replace("▼","").replace("%","").strip()
        try:
            num = float(raw)
            delta_val = num if indicator_color == "green" else -num
        except:
            delta_val = 0

        # value="" stops the duplicate — delta shows the number with colour
        st.metric(
            label=label,
            value="",
            delta=f"{delta_val:.1f}%",
            delta_color="normal"
        )
    else:
        st.metric(label=label, value=value, delta=None)


# ============================================================
# HELPER — VS TARGET CALCULATION
# Returns arrow string and colour based on actual vs target
# ============================================================
def calc_vs(actual, target):
    if target == 0:
        return "N/A", "green"
    pct = ((actual - target) / target) * 100
    if pct >= 0:
        return f"▲{abs(pct):.1f}%", "green"
    else:
        return f"▼{abs(pct):.1f}%", "red"


# ============================================================
# MAIN RENDER FUNCTION — SALES TRACKER
# ============================================================
def render_sales_tracker(df, targets):

    # --------------------------------------------------------
    # DATE BOUNDARIES
    # --------------------------------------------------------
    today = pd.Timestamp.now().normalize()
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    # --------------------------------------------------------
    # PERIOD SLICES
    # --------------------------------------------------------
    df_y = df[df["Date of Order"].dt.normalize() == yesterday]
    df_wtd = df[df["Date of Order"].dt.normalize() >= week_start]
    df_mtd = df[df["Date of Order"].dt.normalize() >= month_start]
    df_ytd = df[df["Date of Order"].dt.normalize() >= year_start]

    # --------------------------------------------------------
    # CALCULATE KPIs PER PERIOD
    # --------------------------------------------------------
    def calc(d):
        return {
            "gmv": d["Revenue (Total Customer Payment)"].sum(),
            "orders": len(d),
            "profit": d["Profit"].sum(),
            "break_even": d["COGS(naira)"].sum() + d["Delivery Cost (how much we paid to the Rider)"].sum()
        }

    y = calc(df_y)
    wtd = calc(df_wtd)
    mtd = calc(df_mtd)
    ytd = calc(df_ytd)

    # --------------------------------------------------------
    # SUMMARY METRICS
    # --------------------------------------------------------
    total_rev = df["Revenue (Total Customer Payment)"].sum()
    total_cogs = df["COGS(naira)"].sum()
    total_profit = df["Profit"].sum()
    total_orders = len(df)
    rev_margin = ((total_rev - total_cogs) / total_rev * 100) if total_rev > 0 else 0
    profit_margin = (total_profit / total_rev * 100) if total_rev > 0 else 0
    avg_daily = total_rev / max(df["Date of Order"].nunique(), 1)
    active = df[df["Date of Order"].dt.normalize() >= today - timedelta(days=30)]["Customer Name"].nunique()
    counts = df.groupby("Customer Name")["Order ID"].count()
    repeat_rate = (counts > 1).sum() / counts.count() * 100 if counts.count() > 0 else 0

    # --------------------------------------------------------
    # TARGETS
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
    # VS LAST WEEK
    # --------------------------------------------------------
    lw_gmv = df[
        (df["Date of Order"].dt.normalize() >= week_start - timedelta(days=7)) &
        (df["Date of Order"].dt.normalize() <= today - timedelta(days=7))
    ]["Revenue (Total Customer Payment)"].sum()
    vs_lw, vs_lw_c = calc_vs(wtd["gmv"], lw_gmv)

    # --------------------------------------------------------
    # VS LAST MONTH
    # --------------------------------------------------------
    days_in = (today - month_start).days
    lm_start = (month_start - timedelta(days=1)).replace(day=1)
    lm_gmv = df[
        (df["Date of Order"].dt.normalize() >= lm_start) &
        (df["Date of Order"].dt.normalize() <= lm_start + timedelta(days=days_in))
    ]["Revenue (Total Customer Payment)"].sum()
    vs_lm, vs_lm_c = calc_vs(mtd["gmv"], lm_gmv)

    # --------------------------------------------------------
    # YTD STATUS
    # --------------------------------------------------------
    if t_ytd > 0:
        pct = ytd["gmv"] / t_ytd
        ytd_status = "🟢 Ahead" if pct >= 1.0 else ("🟡 On Track" if pct >= 0.8 else "🔴 At Risk")
    else:
        ytd_status = "⚪ No Target"

    # --------------------------------------------------------
    # REVENUE TREND
    # --------------------------------------------------------
    trend = df.groupby(["Year", "Month", "Month Name"])[
        "Revenue (Total Customer Payment)"
    ].sum().reset_index().sort_values(["Year", "Month"])
    trend["Label"] = trend.apply(
        lambda r: pd.Timestamp(
            year=int(r["Year"]), month=int(r["Month"]), day=1
        ).strftime("%b %Y"), axis=1
    )

    # ========================================================
    # LAYOUT
    # ========================================================

    # ROW 1
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("<div class='section-title'>📅 Yesterday Sales</div>", unsafe_allow_html=True)
        kpi_card("GMV", format_naira(y["gmv"]))
        kpi_card("Orders", str(y["orders"]))
        kpi_card("Profit", format_naira(y["profit"]))
        kpi_card("Break-Even", format_naira(y["break_even"]))

    with c2:
        st.markdown("<div class='section-title'>📆 WTD Sales</div>", unsafe_allow_html=True)
        kpi_card("GMV", format_naira(wtd["gmv"]))
        kpi_card("Orders", str(wtd["orders"]))
        kpi_card("Vs Last Week", vs_lw, indicator=vs_lw, indicator_color=vs_lw_c)
        vs_wtd, vs_wtd_c = calc_vs(wtd["gmv"], t_wtd)
        kpi_card("Vs Target", vs_wtd, indicator=vs_wtd, indicator_color=vs_wtd_c)

    with c3:
        st.markdown("<div class='section-title'>📊 Summary Metrics</div>", unsafe_allow_html=True)
        rm_str = f"▲{rev_margin:.1f}%" if rev_margin >= 0 else f"▼{abs(rev_margin):.1f}%"
        kpi_card("Revenue Margin", rm_str, indicator=rm_str, indicator_color="green" if rev_margin >= 0 else "red")
        pm_str = f"▲{profit_margin:.1f}%" if profit_margin >= 0 else f"▼{abs(profit_margin):.1f}%"
        kpi_card("Profit Margin", pm_str, indicator=pm_str, indicator_color="green" if profit_margin >= 0 else "red")
        kpi_card("Average Daily Order", format_naira(avg_daily))
        kpi_card("Orders", str(total_orders))
        kpi_card("Active Customers", str(active))
        rr_str = f"▲{repeat_rate:.1f}%"
        kpi_card("Repeat Rate", rr_str, indicator=rr_str, indicator_color="green")

    st.markdown("<br>", unsafe_allow_html=True)

    # ROW 2
    c4, c5, c6 = st.columns([1, 1, 1.5])

    with c4:
        st.markdown("<div class='section-title'>🗓️ MTD Sales</div>", unsafe_allow_html=True)
        kpi_card("GMV", format_naira(mtd["gmv"]))
        kpi_card("Orders", str(mtd["orders"]))
        kpi_card("Vs Last Month", vs_lm, indicator=vs_lm, indicator_color=vs_lm_c)
        vs_mtd, vs_mtd_c = calc_vs(mtd["gmv"], t_mtd)
        kpi_card("Vs Target", vs_mtd, indicator=vs_mtd, indicator_color=vs_mtd_c)

    with c5:
        st.markdown("<div class='section-title'>📈 YTD Sales</div>", unsafe_allow_html=True)
        kpi_card("GMV", format_naira(ytd["gmv"]))
        kpi_card("Orders", str(ytd["orders"]))
        kpi_card("Status", ytd_status)
        vs_ytd, vs_ytd_c = calc_vs(ytd["gmv"], t_ytd)
        kpi_card("Vs Target", vs_ytd, indicator=vs_ytd, indicator_color=vs_ytd_c)

    with c6:
        st.markdown("<div class='section-title'>📉 Revenue Trend</div>", unsafe_allow_html=True)
        if not trend.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=trend["Label"],
                y=trend["Revenue (Total Customer Payment)"],
                mode="lines+markers+text",
                line=dict(color="#003399", width=3),
                marker=dict(color="#003399", size=9),
                text=trend["Revenue (Total Customer Payment)"].apply(format_naira),
                textposition="top center",
                textfont=dict(size=11, color="#333333")
            ))
            fig.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=10, r=20, t=20, b=10),
                xaxis=dict(showgrid=False, title="", tickfont=dict(color="#333333")),
                yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title="", tickfont=dict(color="#333333")),
                showlegend=False, height=300
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available for revenue trend.")