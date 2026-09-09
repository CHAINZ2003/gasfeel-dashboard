# ============================================================
# INSIGHTS.PY — GasFeel CEO Intelligence Briefing
# Auto-generated executive insights from live merged data.
# Covers financial, customer, operations, agent, and product.
# ============================================================

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import timedelta
from supabase import create_client


# ============================================================
# HELPER — FORMAT NAIRA
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
# HELPER — INSIGHT CARD
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
        <div style="background:{c['bg']};border-left:5px solid {c['border']};
                    border-radius:12px;padding:18px 22px;margin-bottom:16px;">
            <div style="font-size:13px;font-weight:800;color:{c['title']};
                        text-transform:uppercase;letter-spacing:0.5px;
                        margin-bottom:8px;">{icon} {title}</div>
            <div style="font-size:14px;color:#333333;line-height:1.7;">{body}</div>
        </div>
    """, unsafe_allow_html=True)


# ============================================================
# HELPER — SNAP KPI CARD (top row metrics)
# ============================================================
def snap(label, value, sub=None, color="#003399"):
    sub_html = f"<div style='font-size:11px;color:{color};font-weight:600;margin-top:4px;'>{sub}</div>" if sub else ""
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
    

# ============================================================
# LOAD AGENT DATA FOR INSIGHTS
# ============================================================
@st.cache_data(ttl=600)
def load_agent_insights():
    try:
        supabase = create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_KEY"]
        )
        all_rows = []
        offset = 0
        while True:
            result = supabase.table("interactions").select(
                "id,agent_id,agent_name,submitted_at,outcome,"
                "revenue,commission_earned,product,customer_whatsapp"
            ).range(offset, offset + 999).execute()
            if not result.data:
                break
            all_rows.extend(result.data)
            if len(result.data) < 1000:
                break
            offset += 1000
        df = pd.DataFrame(all_rows)
        df["submitted_at"] = pd.to_datetime(df["submitted_at"], errors="coerce", utc=True)
        df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce").fillna(0)
        df["commission_earned"] = pd.to_numeric(df["commission_earned"], errors="coerce").fillna(0)
        return df
    except:
        return pd.DataFrame()


# ============================================================
# MAIN RENDER FUNCTION — CEO INSIGHTS
# ============================================================
def render_insights(df, targets):

    today      = pd.Timestamp.now().normalize()
    yesterday  = today - timedelta(days=1)
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    year_start  = today.replace(month=1, day=1)
    last_30    = today - timedelta(days=30)
    last_60    = today - timedelta(days=60)

    # --------------------------------------------------------
    # PRE-CALCULATE ALL METRICS
    # --------------------------------------------------------

    # Revenue model
    total_gmv      = df["GMV"].sum()
    total_revenue  = df["Revenue"].sum()
    total_profit   = df["Profit"].sum()
    total_orders   = len(df)
    total_cogs     = df["COGS(naira)"].sum()
    total_delivery = df["Delivery Cost (how much we paid to the Rider)"].sum()
    profit_margin  = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    revenue_margin = (total_revenue / total_gmv * 100) if total_gmv > 0 else 0

    # Today
    df_today = df[df["Date of Order"].dt.normalize() == today]
    today_gmv = df_today["GMV"].sum()
    today_rev = df_today["Revenue"].sum()
    today_orders = len(df_today)

    # Yesterday
    df_yesterday = df[df["Date of Order"].dt.normalize() == yesterday]
    yesterday_gmv = df_yesterday["GMV"].sum()
    yesterday_rev = df_yesterday["Revenue"].sum()

    # MTD
    df_mtd   = df[df["Date of Order"].dt.normalize() >= month_start]
    mtd_gmv  = df_mtd["GMV"].sum()
    mtd_rev  = df_mtd["Revenue"].sum()
    mtd_prof = df_mtd["Profit"].sum()
    mtd_orders = len(df_mtd)

    # YTD
    df_ytd  = df[df["Date of Order"].dt.normalize() >= year_start]
    ytd_gmv = df_ytd["GMV"].sum()
    ytd_rev = df_ytd["Revenue"].sum()

    # Targets
    def get_target(start, end, col):
        mask = (
            (targets["Period Type"] == "Daily") &
            (targets["Period"] >= start) &
            (targets["Period"] <= end)
        )
        return targets[mask][col].sum()

    t_mtd = get_target(month_start, today, "Target Revenue")
    t_ytd = get_target(year_start, today, "Target Revenue")
    t_today = get_target(today, today, "Target Revenue")

    mtd_vs_target = ((mtd_rev - t_mtd) / t_mtd * 100) if t_mtd > 0 else 0
    ytd_vs_target = ((ytd_rev - t_ytd) / t_ytd * 100) if t_ytd > 0 else 0
    today_vs_target = ((today_rev - t_today) / t_today * 100) if t_today > 0 else 0

    # Last month comparison
    lm_start = (month_start - timedelta(days=1)).replace(day=1)
    lm_end   = month_start - timedelta(days=1)
    lm_rev   = df[
        (df["Date of Order"].dt.normalize() >= lm_start) &
        (df["Date of Order"].dt.normalize() <= lm_end)
    ]["Revenue"].sum()
    mom_growth = ((mtd_rev - lm_rev) / lm_rev * 100) if lm_rev > 0 else 0

    # Customer metrics
    customer_last = df.groupby("Customer Name")["Date of Order"].max().reset_index()
    customer_last.columns = ["Customer Name", "Last Order"]
    customer_last["Days Since"] = (today - customer_last["Last Order"]).dt.days
    total_customers = len(customer_last)
    active_count    = (customer_last["Days Since"] <= 30).sum()
    at_risk_count   = ((customer_last["Days Since"] > 30) & (customer_last["Days Since"] <= 60)).sum()
    churned_count   = (customer_last["Days Since"] > 60).sum()
    churn_rate      = (churned_count / total_customers * 100) if total_customers > 0 else 0
    retention_rate  = (active_count / total_customers * 100) if total_customers > 0 else 0
    counts          = df.groupby("Customer Name")["Order ID"].count()
    repeat_rate     = (counts > 1).sum() / counts.count() * 100 if counts.count() > 0 else 0

    # Top customer
    top_customer        = df.groupby("Customer Name")["Revenue"].sum().idxmax()
    top_customer_rev    = df.groupby("Customer Name")["Revenue"].sum().max()
    top_customer_pct    = (top_customer_rev / total_revenue * 100)

    # Top area
    top_area            = df.groupby("Order Area/Location")["Revenue"].sum().idxmax()
    top_area_rev        = df.groupby("Order Area/Location")["Revenue"].sum().max()
    top_area_pct        = (top_area_rev / total_revenue * 100)

    # Top product
    top_product         = df.groupby("Order Type")["Revenue"].sum().idxmax()
    top_product_pct     = (df.groupby("Order Type")["Revenue"].sum().max() / total_revenue * 100)

    # Best day
    best_day            = df.groupby("Day of the Week")["Revenue"].sum().idxmax()

    # Petrol frequency
    petrol_df = df[df["Order Type"].str.contains("Petrol|PMS", case=False, na=False)]
    if not petrol_df.empty:
        pet_monthly = petrol_df.groupby(["Year", "Month"]).agg(
            Orders=("Order ID", "count"),
            Customers=("Customer Name", "nunique")
        ).reset_index()
        pet_monthly["Freq"] = pet_monthly["Orders"] / pet_monthly["Customers"]
        avg_petrol_freq = pet_monthly["Freq"].mean()
    else:
        avg_petrol_freq = 0

    # Operations
    on_time_rate    = (df["On Time"].sum() / total_orders * 100) if total_orders > 0 else 0
    avg_total_time  = df["Total Duration (mins)"].mean()
    avg_total_time  = avg_total_time if pd.notna(avg_total_time) else 0
    delivery_fee    = df["Delivery Fee (Amount we Collected from the customer)"].sum()
    delivery_profit = delivery_fee - total_delivery
    free_pct        = (df["Delivery Type"] == "Free").sum() / total_orders * 100

    # Agent data
    agent_df = load_agent_insights()
    if not agent_df.empty:
        total_interactions = len(agent_df)
        total_sales_interactions = (agent_df["outcome"] == "sale").sum()
        agent_conversion = (total_sales_interactions / total_interactions * 100) if total_interactions > 0 else 0
        total_commission = agent_df["commission_earned"].sum()
        total_agents = agent_df["agent_id"].nunique()
    else:
        total_interactions = total_sales_interactions = agent_conversion = total_commission = total_agents = 0

    # ========================================================
    # RENDER PAGE
    # ========================================================

    # HEADER
    st.markdown(f"""
        <div style="background:linear-gradient(135deg,#001f6e,#003399);
                    padding:20px 28px;border-radius:12px;margin-bottom:24px;
                    box-shadow:0 4px 15px rgba(0,51,153,0.3);">
            <h2 style="color:white;margin:0;font-size:20px;font-weight:800;">
                🧠 CEO Intelligence Briefing
            </h2>
            <p style="color:#a0c4ff;margin:4px 0 0 0;font-size:13px;">
                Auto-generated · Live merged data · Updated every 10 minutes
            </p>
        </div>
    """, unsafe_allow_html=True)

    # --------------------------------------------------------
    # SNAPSHOT ROW 1 — Today & Financial
    # --------------------------------------------------------
    st.markdown(
        "<div class='section-title'>⚡ Live Snapshot</div>",
        unsafe_allow_html=True
    )

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1:
        snap("Today GMV", format_naira(today_gmv),
             f"{'▲' if today_vs_target >= 0 else '▼'}{abs(today_vs_target):.1f}% vs target",
             "#00aa44" if today_vs_target >= 0 else "#cc0000")
    with k2:
        snap("Today Revenue", format_naira(today_rev),
             f"{today_orders} orders today", "#003399")
    with k3:
        snap("MTD Revenue", format_naira(mtd_rev),
             f"{'▲' if mtd_vs_target >= 0 else '▼'}{abs(mtd_vs_target):.1f}% vs target",
             "#00aa44" if mtd_vs_target >= 0 else "#cc0000")
    with k4:
        snap("YTD Revenue", format_naira(ytd_rev),
             f"{'▲' if ytd_vs_target >= 0 else '▼'}{abs(ytd_vs_target):.1f}% vs target",
             "#00aa44" if ytd_vs_target >= 0 else "#cc0000")
    with k5:
        snap("Profit Margin", f"{profit_margin:.1f}%",
             format_naira(total_profit),
             "#00aa44" if profit_margin >= 15 else "#f0a500")
    with k6:
        snap("Revenue Margin", f"{revenue_margin:.1f}%",
             format_naira(total_revenue), "#003399")

    st.markdown("<br>", unsafe_allow_html=True)

    # SNAPSHOT ROW 2 — Customer & Operations
    k7, k8, k9, k10, k11, k12 = st.columns(6)
    with k7:
        snap("Active Customers", str(active_count),
             f"{retention_rate:.1f}% retention", "#00aa44")
    with k8:
        snap("At Risk", str(at_risk_count),
             f"{(at_risk_count/total_customers*100):.1f}% of base",
             "#f0a500")
    with k9:
        snap("Churned", str(churned_count),
             f"{churn_rate:.1f}% churn rate", "#cc0000")
    with k10:
        snap("Repeat Rate", f"{repeat_rate:.1f}%",
             "customers reordered", "#003399")
    with k11:
        snap("On-Time Rate", f"{on_time_rate:.1f}%",
             "10 min threshold",
             "#00aa44" if on_time_rate >= 70 else "#cc0000")
    with k12:
        snap("Petrol Freq", f"{avg_petrol_freq:.1f}x",
             "orders/customer/month", "#003399")

    st.markdown("<br>", unsafe_allow_html=True)

    # SNAPSHOT ROW 3 — Agent & Delivery
    k13, k14, k15, k16, k17, k18 = st.columns(6)
    with k13:
        snap("Total Orders", f"{total_orders:,}",
             format_naira(total_gmv / max(total_orders, 1)) + " AOV", "#003399")
    with k14:
        snap("Active Agents", str(int(total_agents)),
             f"{total_interactions:,} interactions", "#003399")
    with k15:
        snap("Agent Conv Rate", f"{agent_conversion:.1f}%",
             f"{int(total_sales_interactions)} sales closed",
             "#00aa44" if agent_conversion >= 30 else "#f0a500")
    with k16:
        snap("Commission Paid", format_naira(total_commission),
             "to agents", "#003399")
    with k17:
        snap("Free Delivery", f"{free_pct:.1f}%",
             "of all orders",
             "#f0a500" if free_pct > 50 else "#003399")
    with k18:
        snap("Delivery Profit", format_naira(delivery_profit),
             "fee collected - cost paid",
             "#00aa44" if delivery_profit >= 0 else "#cc0000")

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # SECTION 1 — FINANCIAL PERFORMANCE
    # --------------------------------------------------------
    st.markdown(
        "<div class='section-title'>💰 Financial Performance</div>",
        unsafe_allow_html=True
    )

    # Today vs Yesterday
    if yesterday_rev > 0:
        day_vs_day = ((today_rev - yesterday_rev) / yesterday_rev * 100)
        day_signal = f"<b>{'▲' if day_vs_day >= 0 else '▼'}{abs(day_vs_day):.1f}%</b> vs yesterday's <b>{format_naira(yesterday_rev)}</b>"
        day_color  = "green" if day_vs_day >= 0 else "red"
    else:
        day_signal = "no orders yesterday to compare against"
        day_color  = "blue"

    insight_card(
        "📅", "Today vs Yesterday",
        f"Today GasFeel has generated <b>{format_naira(today_gmv)}</b> GMV and "
        f"<b>{format_naira(today_rev)}</b> revenue from <b>{today_orders}</b> orders. "
        f"Today's revenue is {day_signal}. "
        f"{'On track to hit' if today_vs_target >= 0 else 'Currently'} "
        f"<b>{abs(today_vs_target):.1f}%</b> "
        f"{'above' if today_vs_target >= 0 else 'below'} today's daily revenue target of "
        f"<b>{format_naira(t_today)}</b>.",
        day_color
    )

    # MTD performance
    mtd_color  = "green" if mtd_vs_target >= 0 else "red"
    mtd_signal = f"ahead of target by <b>{abs(mtd_vs_target):.1f}%</b>" if mtd_vs_target >= 0 else f"behind target by <b>{abs(mtd_vs_target):.1f}%</b>"
    insight_card(
        "📊", "Month-to-Date Revenue Performance",
        f"GasFeel has generated <b>{format_naira(mtd_gmv)}</b> GMV and "
        f"<b>{format_naira(mtd_rev)}</b> revenue this month from <b>{mtd_orders:,}</b> orders. "
        f"The business is currently <b>{mtd_signal}</b>. "
        f"Month-over-month revenue change vs same days last month: "
        f"<b>{'▲' if mom_growth >= 0 else '▼'}{abs(mom_growth):.1f}%</b> "
        f"(last month same period: <b>{format_naira(lm_rev)}</b>). "
        f"Projected month-end revenue at current run rate: "
        f"<b>{format_naira(mtd_rev / max((today - month_start).days, 1) * 30)}</b>.",
        mtd_color
    )

    # YTD
    ytd_color  = "green" if ytd_vs_target >= 0 else "red"
    ytd_signal = f"tracking <b>{abs(ytd_vs_target):.1f}%</b> {'above' if ytd_vs_target >= 0 else 'below'} YTD target"
    insight_card(
        "📈", "Year-to-Date Overview",
        f"YTD GMV stands at <b>{format_naira(ytd_gmv)}</b> and revenue at "
        f"<b>{format_naira(ytd_rev)}</b>, {ytd_signal}. "
        f"Overall profit margin is <b>{profit_margin:.1f}%</b> and revenue margin is "
        f"<b>{revenue_margin:.1f}%</b>. Total COGS consumed <b>{format_naira(total_cogs)}</b>.",
        ytd_color
    )

    # --------------------------------------------------------
    # SECTION 2 — CUSTOMER HEALTH
    # --------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-title'>👥 Customer Health</div>",
        unsafe_allow_html=True
    )

    retention_color = "green" if retention_rate >= 50 else "amber" if retention_rate >= 30 else "red"
    insight_card(
        "🔄", "Customer Retention Overview",
        f"Of <b>{total_customers}</b> total customers, <b>{active_count}</b> are active "
        f"(ordered in last 30 days), <b>{at_risk_count}</b> are at risk (31-60 days inactive), "
        f"and <b>{churned_count}</b> have churned (60+ days). "
        f"Retention rate: <b>{retention_rate:.1f}%</b>. "
        f"Churn rate: <b>{churn_rate:.1f}%</b>. "
        f"Repeat purchase rate: <b>{repeat_rate:.1f}%</b>.",
        retention_color
    )

    if churned_count > 0:
        insight_card(
            "⚠️", "Churn Alert",
            f"<b>{churned_count}</b> customers have not ordered in over 60 days — "
            f"<b>{churn_rate:.1f}%</b> of the customer base. "
            f"Estimated recoverable revenue at 30% win-back rate: "
            f"<b>{format_naira(top_customer_rev * churned_count * 0.3)}</b>. "
            f"Priority action: immediate re-engagement campaign targeting these customers.",
            "red"
        )

    insight_card(
        "⛽", "Petrol Purchase Frequency",
        f"On average, a petrol customer orders <b>{avg_petrol_freq:.1f}x per month</b>. "
        f"A typical car refuels every 1-2 weeks meaning GasFeel is capturing approximately "
        f"<b>{'1 in 2' if avg_petrol_freq >= 2 else '1 in 4'} refuels</b> per customer monthly. "
        f"Increasing frequency from <b>{avg_petrol_freq:.1f}x</b> to <b>2.0x</b> per month "
        f"would nearly double petrol revenue with the same customer base. "
        f"Best day for petrol orders: <b>{best_day}</b>.",
        "blue"
    )

    insight_card(
        "🏆", "Top Customer",
        f"<b>{top_customer}</b> is the highest-value customer with "
        f"<b>{format_naira(top_customer_rev)}</b> in revenue — "
        f"<b>{top_customer_pct:.1f}%</b> of total revenue. "
        f"This concentration warrants a dedicated retention strategy.",
        "blue"
    )

    # --------------------------------------------------------
    # SECTION 3 — PRODUCT & AREA
    # --------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-title'>📦 Product & Area Performance</div>",
        unsafe_allow_html=True
    )

    insight_card(
        "🛢️", "Product Mix",
        f"<b>{top_product}</b> dominates at <b>{top_product_pct:.1f}%</b> of revenue. "
        f"Heavy concentration in one product type carries supply and pricing risk. "
        f"<b>{best_day}</b> generates the most revenue — "
        f"rider allocation and stock should be optimised for this day.",
        "blue"
    )

    insight_card(
        "📍", "Top Delivery Area",
        f"<b>{top_area}</b> is the highest-revenue area at "
        f"<b>{format_naira(top_area_rev)}</b> — "
        f"<b>{top_area_pct:.1f}%</b> of total revenue. "
        f"Priority rider assignment and pre-positioned stock in this area "
        f"will protect the largest revenue stream.",
        "blue"
    )

    # --------------------------------------------------------
    # SECTION 4 — AGENT PERFORMANCE
    # --------------------------------------------------------
    if not agent_df.empty:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            "<div class='section-title'>👤 Agent Performance</div>",
            unsafe_allow_html=True
        )

        agent_conv_color = "green" if agent_conversion >= 30 else "amber" if agent_conversion >= 15 else "red"
        insight_card(
            "🎯", "Agent Conversion",
            f"<b>{int(total_agents)}</b> agents have logged <b>{total_interactions:,}</b> "
            f"interactions and closed <b>{int(total_sales_interactions)}</b> sales. "
            f"Overall conversion rate is <b>{agent_conversion:.1f}%</b> — "
            f"{'strong performance above the 30% benchmark' if agent_conversion >= 30 else 'below the 30% benchmark, coaching recommended'}. "
            f"Total commission earned by agents: <b>{format_naira(total_commission)}</b>.",
            agent_conv_color
        )

    # --------------------------------------------------------
    # SECTION 5 — OPERATIONS
    # --------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-title'>🚴 Operations</div>",
        unsafe_allow_html=True
    )

    ops_color = "green" if on_time_rate >= 70 else "amber" if on_time_rate >= 50 else "red"
    insight_card(
        "⏱️", "Delivery Performance",
        f"On-time delivery rate (within 10 minutes) is <b>{on_time_rate:.1f}%</b>. "
        f"Average total order time from placement to completion is "
        f"<b>{avg_total_time:.1f} minutes</b>. "
        f"{'Performance is strong — maintain current rider allocation.' if on_time_rate >= 70 else 'Below target — review rider capacity, station proximity, and fulfillment process.'}",
        ops_color
    )

    free_color = "amber" if free_pct > 50 else "green"
    insight_card(
        "🆓", "Delivery Economics",
        f"<b>{free_pct:.1f}%</b> of orders received free delivery. "
        f"Delivery cost paid to riders: <b>{format_naira(total_delivery)}</b>. "
        f"Delivery fees collected from customers: <b>{format_naira(delivery_fee)}</b>. "
        f"Net delivery {'profit' if delivery_profit >= 0 else 'loss'}: "
        f"<b>{format_naira(abs(delivery_profit))}</b>. "
        f"{'Consider reviewing free delivery eligibility to reduce subsidy.' if free_pct > 50 else 'Delivery fee collection is healthy.'}",
        free_color
    )



# ============================================================
# HELPER — CHART DESCRIPTION
# Shows a small explanatory note below every chart title.
# Helps team members understand what each chart means.
# ============================================================
def chart_note(text):
    st.markdown(f"""
        <p style='color:#888;font-size:12px;font-style:italic;
                  margin:-8px 0 10px 0;line-height:1.5;'>
            💡 {text}
        </p>
    """, unsafe_allow_html=True)