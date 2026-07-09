# ============================================================
# INSIGHTS.PY — GasFeel CEO Intelligence Summary
# Automatically generates executive-level insights from live data.
# Called from app.py as a 6th tab.
# ============================================================

import streamlit as st
import pandas as pd
from datetime import timedelta


# ============================================================
# HELPER — FORMAT NAIRA
# ============================================================
def format_naira(value):
    if value >= 1_000_000:
        return f"₦{value/1_000_000:.2f}M"
    elif value >= 1_000:
        return f"₦{value/1_000:.2f}K"
    else:
        return f"₦{value:,.0f}"


# ============================================================
# HELPER — INSIGHT CARD
# Renders a styled insight block with icon, title, and body.
# color: "blue", "green", "red", "amber"
# ============================================================
def insight_card(icon, title, body, color="blue"):
    colors = {
        "blue":  {"bg": "#eef2ff", "border": "#003399", "title": "#001f6e"},
        "green": {"bg": "#efffef", "border": "#00aa44", "title": "#006622"},
        "red":   {"bg": "#fff0f0", "border": "#cc0000", "title": "#990000"},
        "amber": {"bg": "#fff8e6", "border": "#f0a500", "title": "#b37a00"},
    }
    c = colors.get(color, colors["blue"])
    st.markdown(f"""
        <div style="
            background:{c['bg']};
            border-left:5px solid {c['border']};
            border-radius:12px;
            padding:18px 22px;
            margin-bottom:16px;
        ">
            <div style="font-size:13px;font-weight:800;color:{c['title']};
                        text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">
                {icon} {title}
            </div>
            <div style="font-size:14px;color:#333333;line-height:1.7;">
                {body}
            </div>
        </div>
    """, unsafe_allow_html=True)


# ============================================================
# MAIN RENDER FUNCTION — CEO INSIGHTS
# ============================================================
def render_insights(df, targets):

    today = pd.Timestamp.now().normalize()
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    last_30 = today - timedelta(days=30)
    last_60 = today - timedelta(days=60)

    # --------------------------------------------------------
    # PRE-CALCULATE ALL METRICS NEEDED FOR INSIGHTS
    # --------------------------------------------------------

    # Revenue model
    total_gmv = df["GMV"].sum()
    total_revenue = df["Revenue"].sum()
    total_profit = df["Profit"].sum()
    total_orders = len(df)
    total_cogs = df["COGS(naira)"].sum()
    total_delivery_cost = df["Delivery Cost (how much we paid to the Rider)"].sum()
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    revenue_margin = (total_revenue / total_gmv * 100) if total_gmv > 0 else 0

    # MTD
    df_mtd = df[df["Date of Order"].dt.normalize() >= month_start]
    mtd_gmv = df_mtd["GMV"].sum()
    mtd_revenue = df_mtd["Revenue"].sum()
    mtd_profit = df_mtd["Profit"].sum()
    mtd_orders = len(df_mtd)

    # MTD targets
    def get_target(start, end, col):
        mask = (
            (targets["Period Type"] == "Daily") &
            (targets["Period"] >= start) &
            (targets["Period"] <= end)
        )
        return targets[mask][col].sum()

    t_mtd_gmv = get_target(month_start, today, "Target GMV")
    t_ytd_gmv = get_target(year_start, today, "Target GMV")
    ytd_gmv = df[df["Date of Order"].dt.normalize() >= year_start]["GMV"].sum()

    mtd_vs_target = ((mtd_gmv - t_mtd_gmv) / t_mtd_gmv * 100) if t_mtd_gmv > 0 else 0
    ytd_vs_target = ((ytd_gmv - t_ytd_gmv) / t_ytd_gmv * 100) if t_ytd_gmv > 0 else 0

    # Last month comparison
    lm_start = (month_start - timedelta(days=1)).replace(day=1)
    lm_end = month_start - timedelta(days=1)
    lm_gmv = df[
        (df["Date of Order"].dt.normalize() >= lm_start) &
        (df["Date of Order"].dt.normalize() <= lm_end)
    ]["GMV"].sum()
    mom_growth = ((mtd_gmv - lm_gmv) / lm_gmv * 100) if lm_gmv > 0 else 0

    # Customer metrics
    customer_last = df.groupby("Customer Name")["Date of Order"].max().reset_index()
    customer_last.columns = ["Customer Name", "Last Order"]
    customer_last["Days Since"] = (today - customer_last["Last Order"]).dt.days
    active_count = (customer_last["Days Since"] <= 30).sum()
    at_risk_count = ((customer_last["Days Since"] > 30) & (customer_last["Days Since"] <= 60)).sum()
    churned_count = (customer_last["Days Since"] > 60).sum()
    total_customers = len(customer_last)
    churn_rate = (churned_count / total_customers * 100) if total_customers > 0 else 0
    retention_rate = (active_count / total_customers * 100) if total_customers > 0 else 0

    # Top customer
    top_customer = df.groupby("Customer Name")["Revenue"].sum().idxmax()
    top_customer_revenue = df.groupby("Customer Name")["Revenue"].sum().max()

    # Top area
    top_area = df.groupby("Order Area/Location")["Revenue"].sum().idxmax()
    top_area_revenue = df.groupby("Order Area/Location")["Revenue"].sum().max()

    # Top product
    top_product = df.groupby("Order Type")["Revenue"].sum().idxmax()
    top_product_pct = (df.groupby("Order Type")["Revenue"].sum().max() / total_revenue * 100)

    # Best day
    best_day = df.groupby("Day of the Week")["Revenue"].sum().idxmax()

    # Rider performance
    on_time_rate = (df["On Time"].sum() / total_orders * 100) if total_orders > 0 else 0
    avg_total_time = df["Total Duration (mins)"].mean()

    # Free vs paid
    free_pct = (df["Delivery Type"] == "Free").sum() / total_orders * 100

    # Delivery profit
    delivery_fee = df["Delivery Fee (Amount we Collected from the customer)"].sum()
    delivery_profit = delivery_fee - total_delivery_cost
    delivery_profit_pct = (delivery_profit / total_delivery_cost * 100) if total_delivery_cost > 0 else 0

    # Repeat rate
    counts = df.groupby("Customer Name")["Order ID"].count()
    repeat_rate = (counts > 1).sum() / counts.count() * 100 if counts.count() > 0 else 0

    # ========================================================
    # RENDER INSIGHTS PAGE
    # ========================================================

    # ========================================================
    # HEADER
    # ========================================================
    st.markdown(f"""
        <div style="
            background:linear-gradient(135deg,#001f6e,#003399);
            padding:20px 28px;border-radius:12px;
            margin-bottom:24px;
            box-shadow:0 4px 15px rgba(0,51,153,0.3);
        ">
            <h2 style="color:white;margin:0;font-size:20px;font-weight:800;">
                🧠 CEO Intelligence Briefing
            </h2>
            <p style="color:#a0c4ff;margin:4px 0 0 0;font-size:13px;">
                Auto-generated from live GasFeel data · Updated every 10 minutes
            </p>
        </div>
    """, unsafe_allow_html=True)

    # ========================================================
    # CEO KPI SNAPSHOT — Top row of key numbers
    # ========================================================
    st.markdown("<div class='section-title'>⚡ Key Metrics Snapshot</div>", unsafe_allow_html=True)

    k1, k2, k3, k4, k5, k6 = st.columns(6)

    def snap_card(col, label, value, delta=None, color="#003399"):
        with col:
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
                    {"" if not delta else f"<div style='font-size:12px;font-weight:700;margin-top:4px;color:{color};'>{delta}</div>"}
                </div>
            """, unsafe_allow_html=True)

    snap_card(k1, "YTD GMV", format_naira(ytd_gmv), f"{'▲' if ytd_vs_target>=0 else '▼'}{abs(ytd_vs_target):.1f}% vs target", "#003399" if ytd_vs_target>=0 else "#cc0000")
    snap_card(k2, "YTD Revenue", format_naira(total_revenue), f"{revenue_margin:.1f}% margin", "#003399")
    snap_card(k3, "Profit Margin", f"{profit_margin:.1f}%", format_naira(total_profit), "#00aa44" if profit_margin >= 15 else "#f0a500")
    snap_card(k4, "Active Customers", str(active_count), f"{retention_rate:.1f}% retention", "#00aa44")
    snap_card(k5, "At Risk", str(at_risk_count), f"{(at_risk_count/total_customers*100):.1f}% of base", "#f0a500")
    snap_card(k6, "Churned", str(churned_count), f"{churn_rate:.1f}% churn rate", "#cc0000")

    st.markdown("<br>", unsafe_allow_html=True)

    # Second KPI row
    k7, k8, k9, k10, k11, k12 = st.columns(6)

    snap_card(k7, "Total Orders", f"{total_orders:,}", f"{format_naira(total_gmv/max(total_orders,1))} AOV", "#003399")
    snap_card(k8, "Repeat Rate", f"{repeat_rate:.1f}%", "customers reordered", "#003399")
    snap_card(k9, "On-Time Rate", f"{on_time_rate:.1f}%", "10 min threshold", "#00aa44" if on_time_rate>=70 else "#cc0000")
    snap_card(k10, "Avg Delivery", f"{avg_total_time:.1f} mins", "order to completion", "#003399")
    snap_card(k11, "Free Delivery", f"{free_pct:.1f}%", "of all orders", "#f0a500" if free_pct>50 else "#003399")
    snap_card(k12, "Delivery Profit", format_naira(delivery_profit), "fee collected - cost", "#00aa44" if delivery_profit>=0 else "#cc0000")

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # SECTION 1 — FINANCIAL PERFORMANCE
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>💰 Financial Performance</div>", unsafe_allow_html=True)

    # MTD performance
    if mtd_vs_target >= 0:
        mtd_color = "green"
        mtd_signal = f"ahead of target by <b>{abs(mtd_vs_target):.1f}%</b>"
    else:
        mtd_color = "red"
        mtd_signal = f"behind target by <b>{abs(mtd_vs_target):.1f}%</b>"

    insight_card(
        "📊", "Month-to-Date Revenue Performance",
        f"GasFeel has generated <b>{format_naira(mtd_gmv)}</b> in GMV this month with "
        f"<b>{format_naira(mtd_revenue)}</b> in revenue and <b>{format_naira(mtd_profit)}</b> in profit. "
        f"The business is currently <b>{mtd_signal}</b> against monthly targets. "
        f"At this run rate, the projected month-end GMV is "
        f"<b>{format_naira(mtd_gmv / max((today - month_start).days, 1) * 30)}</b>.",
        mtd_color
    )

    # YTD performance
    if ytd_vs_target >= 0:
        ytd_color = "green"
        ytd_signal = f"tracking <b>{abs(ytd_vs_target):.1f}%</b> above YTD target"
    else:
        ytd_color = "red"
        ytd_signal = f"tracking <b>{abs(ytd_vs_target):.1f}%</b> below YTD target"

    insight_card(
        "📈", "Year-to-Date Overview",
        f"Year-to-date GMV stands at <b>{format_naira(ytd_gmv)}</b>, {ytd_signal}. "
        f"Overall profit margin is <b>{profit_margin:.1f}%</b> and revenue margin is "
        f"<b>{revenue_margin:.1f}%</b>. "
        f"Total COGS consumed <b>{format_naira(total_cogs)}</b> of GMV this period.",
        ytd_color
    )

    # MoM growth
    if mom_growth >= 0:
        mom_color = "green"
        mom_signal = f"up <b>{mom_growth:.1f}%</b> vs last month"
    else:
        mom_color = "red"
        mom_signal = f"down <b>{abs(mom_growth):.1f}%</b> vs last month"

    insight_card(
        "📉", "Month-over-Month Growth",
        f"This month's GMV of <b>{format_naira(mtd_gmv)}</b> is {mom_signal} "
        f"(<b>{format_naira(lm_gmv)}</b>). "
        f"The business processed <b>{mtd_orders:,}</b> orders this month at an average order value "
        f"of <b>{format_naira(mtd_gmv / max(mtd_orders, 1))}</b>.",
        mom_color
    )

    # --------------------------------------------------------
    # SECTION 2 — CUSTOMER HEALTH
    # --------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>👥 Customer Health</div>", unsafe_allow_html=True)

    # Retention
    retention_color = "green" if retention_rate >= 50 else "amber" if retention_rate >= 30 else "red"
    insight_card(
        "🔄", "Customer Retention",
        f"Of <b>{total_customers}</b> total customers, <b>{active_count}</b> are active (ordered in last 30 days), "
        f"<b>{at_risk_count}</b> are at risk (31-60 days inactive), and "
        f"<b>{churned_count}</b> have churned (60+ days inactive). "
        f"Retention rate stands at <b>{retention_rate:.1f}%</b> and churn rate at <b>{churn_rate:.1f}%</b>. "
        f"Repeat purchase rate is <b>{repeat_rate:.1f}%</b>.",
        retention_color
    )

    # Churn alert
    if churned_count > 0:
        insight_card(
            "⚠️", "Churn Alert",
            f"<b>{churned_count}</b> customers have not placed an order in over 60 days. "
            f"This represents <b>{churn_rate:.1f}%</b> of the total customer base. "
            f"Immediate re-engagement campaigns targeting these customers could recover "
            f"an estimated <b>{format_naira(top_customer_revenue * churned_count * 0.3)}</b> in potential revenue "
            f"assuming a 30% win-back rate.",
            "red"
        )

    # Top customer
    insight_card(
        "🏆", "Top Customer",
        f"<b>{top_customer}</b> is the highest-value customer, generating <b>{format_naira(top_customer_revenue)}</b> "
        f"in revenue — representing <b>{(top_customer_revenue/total_revenue*100):.1f}%</b> of total revenue. "
        f"This level of concentration is worth monitoring; consider loyalty incentives to retain this customer.",
        "blue"
    )

    # --------------------------------------------------------
    # SECTION 3 — PRODUCT & AREA PERFORMANCE
    # --------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>📦 Product & Area Performance</div>", unsafe_allow_html=True)

    insight_card(
        "🛢️", "Product Mix",
        f"<b>{top_product}</b> is the dominant product category, contributing "
        f"<b>{top_product_pct:.1f}%</b> of total revenue. "
        f"Revenue concentration in one product type carries supply risk — "
        f"consider strategies to grow the secondary product categories. "
        f"<b>{best_day}</b> is the highest revenue day of the week; "
        f"staffing and inventory should be optimised for this day.",
        "blue"
    )

    insight_card(
        "📍", "Top Location",
        f"<b>{top_area}</b> is the highest-revenue delivery area, generating "
        f"<b>{format_naira(top_area_revenue)}</b> — "
        f"<b>{(top_area_revenue/total_revenue*100):.1f}%</b> of total revenue. "
        f"This area warrants priority rider assignment and stock allocation. "
        f"Lower-performing areas may represent untapped growth opportunity.",
        "blue"
    )

    # --------------------------------------------------------
    # SECTION 4 — OPERATIONS
    # --------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>🚴 Operations</div>", unsafe_allow_html=True)

    ops_color = "green" if on_time_rate >= 70 else "amber" if on_time_rate >= 50 else "red"
    insight_card(
        "⏱️", "Delivery Performance",
        f"On-time delivery rate (orders completed within 10 minutes) is <b>{on_time_rate:.1f}%</b>. "
        f"Average total order time from placement to completion is <b>{avg_total_time:.1f} minutes</b>. "
        f"{'Performance is strong — maintain current rider allocation.' if on_time_rate >= 70 else 'Performance needs improvement — review rider capacity and station proximity.'}",
        ops_color
    )

    free_color = "amber" if free_pct > 50 else "green"
    insight_card(
        "🆓", "Delivery Subsidy",
        f"<b>{free_pct:.1f}%</b> of orders received free delivery. "
        f"Delivery cost paid to riders totalled <b>{format_naira(total_delivery_cost)}</b> "
        f"while delivery fees collected from customers totalled <b>{format_naira(delivery_fee)}</b>, "
        f"resulting in a net delivery {'profit' if delivery_profit >= 0 else 'loss'} of "
        f"<b>{format_naira(abs(delivery_profit))}</b>. "
        f"{'Consider reviewing free delivery eligibility criteria to reduce subsidy cost.' if free_pct > 50 else 'Delivery fee collection is healthy.'}",
        free_color
    )