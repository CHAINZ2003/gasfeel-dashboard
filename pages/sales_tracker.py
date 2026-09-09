# ============================================================
# SALES TRACKER TAB — GasFeel Dashboard
# Shows Today, WTD, MTD, YTD KPIs, Summary Metrics,
# and Revenue Trend chart with descriptions.
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
# Returns arrow string and color only
# ============================================================
def calc_vs(actual, compare):
    if compare == 0:
        return "N/A", "green"
    pct = ((actual - compare) / compare) * 100
    arrow = f"▲{abs(pct):.1f}%" if pct >= 0 else f"▼{abs(pct):.1f}%"
    color = "green" if pct >= 0 else "red"
    return arrow, color


# ============================================================
# HELPER — CHART DESCRIPTION
# Shows a small explanatory note below every chart title.
# ============================================================
def chart_note(text):
    st.markdown(f"""
        <p style='color:#888;font-size:12px;font-style:italic;
                  margin:-8px 0 10px 0;line-height:1.5;'>
            💡 {text}
        </p>
    """, unsafe_allow_html=True)


# ============================================================
# MAIN RENDER FUNCTION — SALES TRACKER
# ============================================================
def render_sales_tracker(df, targets):

    # --------------------------------------------------------
    # STEP 1 — DATE BOUNDARIES
    # --------------------------------------------------------
    today       = pd.Timestamp.now().normalize()
    yesterday   = today - timedelta(days=1)
    week_start  = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    year_start  = today.replace(month=1, day=1)

    # --------------------------------------------------------
    # STEP 2 — FILTER DATA INTO TIME PERIODS
    # --------------------------------------------------------
    df_y   = df[df["Date of Order"].dt.normalize() == today]
    df_wtd = df[df["Date of Order"].dt.normalize() >= week_start]
    df_mtd = df[df["Date of Order"].dt.normalize() >= month_start]
    df_ytd = df[df["Date of Order"].dt.normalize() >= year_start]

    # --------------------------------------------------------
    # STEP 3 — CALCULATE KPIs PER PERIOD
    # --------------------------------------------------------
    def calc(d):
        return {
            "gmv":        d["GMV"].sum(),
            "revenue":    d["Revenue"].sum(),
            "orders":     len(d),
            "profit":     d["Profit"].sum(),
            "break_even": d["COGS(naira)"].sum() + d[
                "Delivery Cost (how much we paid to the Rider)"
            ].sum()
        }

    y   = calc(df_y)
    wtd = calc(df_wtd)
    mtd = calc(df_mtd)
    ytd = calc(df_ytd)

    # --------------------------------------------------------
    # STEP 4 — SUMMARY METRICS
    # --------------------------------------------------------
    total_gmv     = df["GMV"].sum()
    total_rev     = df["Revenue"].sum()
    total_profit  = df["Profit"].sum()
    total_orders  = len(df)
    rev_margin    = (total_rev / total_gmv * 100) if total_gmv > 0 else 0
    profit_margin = (total_profit / total_rev * 100) if total_rev > 0 else 0
    avg_daily     = total_rev / max(df["Date of Order"].nunique(), 1)
    active        = df[
        df["Date of Order"].dt.normalize() >= today - timedelta(days=30)
    ]["Customer Name"].nunique()
    counts        = df.groupby("Customer Name")["Order ID"].count()
    repeat_rate   = (counts > 1).sum() / counts.count() * 100 if counts.count() > 0 else 0

    # --------------------------------------------------------
    # STEP 5 — TARGET LOOKUPS
    # --------------------------------------------------------
    def get_target(start, end, col):
        mask = (
            (targets["Period Type"] == "Daily") &
            (targets["Period"] >= start) &
            (targets["Period"] <= end)
        )
        return targets[mask][col].sum()

    t_today_revenue = get_target(today, today, "Target Revenue")
    t_today_gmv     = get_target(today, today, "Target GMV")
    t_wtd_revenue   = get_target(week_start, today, "Target Revenue")
    t_mtd_revenue   = get_target(month_start, today, "Target Revenue")
    t_ytd_revenue   = get_target(year_start, today, "Target Revenue")

    # --------------------------------------------------------
    # STEP 6 — VS YESTERDAY
    # --------------------------------------------------------
    df_yesterday_compare = df[df["Date of Order"].dt.normalize() == yesterday]
    yesterday_gmv        = df_yesterday_compare["GMV"].sum()
    yesterday_revenue    = df_yesterday_compare["Revenue"].sum()

    # --------------------------------------------------------
    # STEP 7 — VS LAST WEEK
    # --------------------------------------------------------
    lw_start   = week_start - timedelta(days=7)
    lw_end     = today - timedelta(days=7)
    lw_revenue = df[
        (df["Date of Order"].dt.normalize() >= lw_start) &
        (df["Date of Order"].dt.normalize() <= lw_end)
    ]["Revenue"].sum()

    # --------------------------------------------------------
    # STEP 8 — VS LAST MONTH
    # --------------------------------------------------------
    days_in    = (today - month_start).days
    lm_start   = (month_start - timedelta(days=1)).replace(day=1)
    lm_end     = lm_start + timedelta(days=days_in)
    lm_revenue = df[
        (df["Date of Order"].dt.normalize() >= lm_start) &
        (df["Date of Order"].dt.normalize() <= lm_end)
    ]["Revenue"].sum()

    # --------------------------------------------------------
    # STEP 9 — YTD STATUS
    # --------------------------------------------------------
    if t_ytd_revenue > 0:
        pct_ytd    = ytd["revenue"] / t_ytd_revenue
        ytd_status = "🟢 Ahead" if pct_ytd >= 1.0 else (
                     "🟡 On Track" if pct_ytd >= 0.8 else "🔴 At Risk")
    else:
        ytd_status = "⚪ No Target"

    # --------------------------------------------------------
    # STEP 10 — REVENUE TREND
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

    # --------------------------------------------------------
    # ROW 1 — Today | WTD | Summary Metrics
    # --------------------------------------------------------
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            "<div class='section-title'>📅 Today's Sales</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Real-time snapshot of today's performance. "
            "GMV is the total amount customers paid. "
            "Revenue is what GasFeel keeps after product cost. "
            "Profit is what remains after delivery cost too. "
            "Break-Even is the minimum needed to cover all costs."
        )
        kpi_card("GMV",        format_naira(y["gmv"]))
        kpi_card("Revenue",    format_naira(y["revenue"]))
        kpi_card("Orders",     str(y["orders"]))
        kpi_card("Profit",     format_naira(y["profit"]))
        kpi_card("Break-Even", format_naira(y["break_even"]))

        # Vs Yesterday
        if yesterday_gmv > 0:
            pct_vs_yday  = ((y["gmv"] - yesterday_gmv) / yesterday_gmv * 100)
            arrow_yday   = f"▲{abs(pct_vs_yday):.1f}%" if pct_vs_yday >= 0 else f"▼{abs(pct_vs_yday):.1f}%"
            color_yday   = "green" if pct_vs_yday >= 0 else "red"
            indicator_card("Vs Yesterday GMV", format_naira(yesterday_gmv), arrow_yday, color_yday)

        # Vs Today Target
        if t_today_revenue > 0:
            pct_today  = ((y["revenue"] - t_today_revenue) / t_today_revenue * 100)
            arrow_today = f"▲{abs(pct_today):.1f}%" if pct_today >= 0 else f"▼{abs(pct_today):.1f}%"
            color_today = "green" if pct_today >= 0 else "red"
            indicator_card("Vs Target Revenue", format_naira(t_today_revenue), arrow_today, color_today)

    with c2:
        st.markdown(
            "<div class='section-title'>📆 WTD Sales</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Week-to-date performance from Monday to today. "
            "Vs Last Week compares same number of days last week — "
            "green means improvement, red means decline. "
            "Vs Target shows how this week's revenue tracks "
            "against the sum of daily targets set for this week."
        )
        kpi_card("GMV",     format_naira(wtd["gmv"]))
        kpi_card("Revenue", format_naira(wtd["revenue"]))
        kpi_card("Orders",  str(wtd["orders"]))

        vs_lw, vs_lw_c = calc_vs(wtd["revenue"], lw_revenue)
        indicator_card("Vs Last Week", format_naira(lw_revenue), vs_lw, vs_lw_c)

        vs_wtd, vs_wtd_c = calc_vs(wtd["revenue"], t_wtd_revenue)
        indicator_card("Vs Target Revenue", format_naira(t_wtd_revenue), vs_wtd, vs_wtd_c)

    with c3:
        st.markdown(
            "<div class='section-title'>📊 Summary Metrics</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Overall performance across the selected filter period. "
            "Revenue Margin = Revenue ÷ GMV — how much GasFeel keeps "
            "from every naira a customer pays before delivery cost. "
            "Profit Margin = Profit ÷ Revenue — true profitability. "
            "Repeat Rate = customers who ordered more than once."
        )

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

    # --------------------------------------------------------
    # ROW 2 — MTD | YTD | Revenue Trend Chart
    # --------------------------------------------------------
    c4, c5, c6 = st.columns([1, 1, 1.5])

    with c4:
        st.markdown(
            "<div class='section-title'>🗓️ MTD Sales</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Month-to-date from the 1st to today. "
            "Vs Last Month compares the same number of days "
            "into last month — fair like-for-like comparison. "
            "Vs Target shows actual revenue against the sum "
            "of daily targets from the 1st to today."
        )
        kpi_card("GMV",     format_naira(mtd["gmv"]))
        kpi_card("Revenue", format_naira(mtd["revenue"]))
        kpi_card("Orders",  str(mtd["orders"]))

        vs_lm, vs_lm_c = calc_vs(mtd["revenue"], lm_revenue)
        indicator_card("Vs Last Month", format_naira(lm_revenue), vs_lm, vs_lm_c)

        vs_mtd, vs_mtd_c = calc_vs(mtd["revenue"], t_mtd_revenue)
        indicator_card("Vs Target Revenue", format_naira(t_mtd_revenue), vs_mtd, vs_mtd_c)

    with c5:
        st.markdown(
            "<div class='section-title'>📈 YTD Sales</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Year-to-date from January 1st to today. "
            "Status shows whether GasFeel is Ahead, On Track, "
            "or At Risk based on cumulative revenue vs cumulative "
            "daily targets. At Risk means below 80% of target. "
            "Vs Target shows the YTD target revenue amount."
        )
        kpi_card("GMV",     format_naira(ytd["gmv"]))
        kpi_card("Revenue", format_naira(ytd["revenue"]))
        kpi_card("Orders",  str(ytd["orders"]))
        kpi_card("Status",  ytd_status)

        vs_ytd, vs_ytd_c = calc_vs(ytd["revenue"], t_ytd_revenue)
        indicator_card("Vs Target Revenue", format_naira(t_ytd_revenue), vs_ytd, vs_ytd_c)

    with c6:
        st.markdown(
            "<div class='section-title'>📉 Revenue Trend</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Monthly revenue trend across the selected period. "
            "Each point shows total revenue for that month. "
            "Rising trend = business growing. "
            "Falling trend = investigate causes — seasonality, "
            "churn, pricing changes, or supply issues."
        )
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