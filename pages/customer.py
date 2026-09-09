# ============================================================
# CUSTOMER TAB — GasFeel Dashboard
# Shows Customer Analytics.
# Charts: Top customers, customer status, high value customers,
# LTV by area, customer distribution, status by month,
# churn rate by area, and customer lists by status.
# All charts include descriptions for team readability.
# ============================================================

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import timedelta


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
# HELPER — KPI CARD
# ============================================================
def kpi_card(label, value, color="kpi-value"):
    st.markdown(f"""
        <div class='kpi-card'>
            <div class='kpi-label'>{label}</div>
            <div class='{color}'>{value}</div>
        </div>
    """, unsafe_allow_html=True)


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
# MAIN RENDER FUNCTION — CUSTOMER TAB
# ============================================================
def render_customer(df):

    today = pd.Timestamp.now().normalize()

    # --------------------------------------------------------
    # CALCULATE CUSTOMER STATUS
    # Active = ordered in last 30 days
    # At Risk = last order 31-60 days ago
    # Churned = no order in 60+ days
    # --------------------------------------------------------
    last_order = df.groupby("Customer Name")["Date of Order"].max().reset_index()
    last_order.columns = ["Customer Name", "Last Order Date"]
    last_order["Days Since Order"] = (today - last_order["Last Order Date"]).dt.days

    def assign_status(days):
        if days <= 30:
            return "Active"
        elif days <= 60:
            return "At Risk"
        else:
            return "Churned"

    last_order["Status"] = last_order["Days Since Order"].apply(assign_status)

    status_counts  = last_order["Status"].value_counts()
    total_customers = len(last_order)
    active_count   = status_counts.get("Active", 0)
    at_risk_count  = status_counts.get("At Risk", 0)
    churned_count  = status_counts.get("Churned", 0)

    # --------------------------------------------------------
    # TOP-LINE KPIs
    # --------------------------------------------------------
    total_revenue    = df["Revenue"].sum()
    total_orders     = len(df)
    avg_order_value  = total_revenue / total_orders if total_orders > 0 else 0
    total_profit     = df["Profit"].sum()
    profit_per_cust  = total_profit / total_customers if total_customers > 0 else 0

    # --------------------------------------------------------
    # TOP KPI ROW
    # --------------------------------------------------------
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        kpi_card("Total Customers", f"{total_customers:,}")
    with k2:
        st.markdown(f"""
            <div class='kpi-card'>
                <div class='kpi-label'>Active Customers</div>
                <div class='kpi-value'>{active_count}</div>
                <div class='kpi-label' style='margin-top:6px;'>
                    Churned: <b>{churned_count}</b>
                </div>
            </div>
        """, unsafe_allow_html=True)
    with k3:
        kpi_card("Avg Order Value", format_naira(avg_order_value))
    with k4:
        kpi_card("Profit / Customer", format_naira(profit_per_cust))

    st.markdown("""
        <p style='color:#888;font-size:12px;font-style:italic;margin:4px 0 16px 0;'>
            💡 Active = ordered in last 30 days.
            Churned = no order in 60+ days.
            Avg Order Value = Revenue ÷ Total Orders.
            Profit per Customer = Total Profit ÷ Unique Customers.
        </p>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # ROW 2 — Top Customers | Customer Status | High Value
    # --------------------------------------------------------
    row1_left, row1_mid, row1_right = st.columns(3)

    # ---- CHART 1: Top Customers by Revenue ----
    with row1_left:
        st.markdown(
            "<div class='section-title'>🏆 Top Customers by Revenue</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Your 8 highest-revenue customers ranked by total revenue. "
            "The label shows GMV (total payment) and Revenue (after product cost). "
            "These customers deserve priority service and loyalty incentives — "
            "losing even one of them has a significant revenue impact."
        )

        top_customers = df.groupby("Customer Name").agg(
            Revenue=("Revenue", "sum"),
            GMV=("GMV", "sum")
        ).reset_index().sort_values("Revenue", ascending=True).tail(8)

        top_customers["Label"] = top_customers.apply(
            lambda r: f"GMV: {format_naira(r['GMV'])} | Rev: {format_naira(r['Revenue'])}",
            axis=1
        )

        fig_top = go.Figure()
        fig_top.add_trace(go.Bar(
            x=top_customers["Revenue"],
            y=top_customers["Customer Name"],
            orientation="h",
            text=top_customers["Label"],
            textposition="outside",
            textfont=dict(size=9, color="#333333"),
            marker_color="#003399"
        ))
        fig_top.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=5, r=200, t=10, b=5),
            xaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            yaxis=dict(showgrid=False, title=""),
            height=300
        )
        st.plotly_chart(fig_top, use_container_width=True)

    # ---- CHART 2: Customer Status ----
    with row1_mid:
        st.markdown(
            "<div class='section-title'>📊 Customer Status</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Current health of your customer base. "
            "Blue = Active (ordered in last 30 days). "
            "Amber = At Risk (31-60 days since last order — needs outreach). "
            "Red = Churned (60+ days — likely gone to a competitor). "
            "A growing red bar is a critical warning sign."
        )

        status_df = pd.DataFrame({
            "Status": ["Active", "At Risk", "Churned"],
            "Count":  [active_count, at_risk_count, churned_count]
        })
        color_map = {
            "Active":  "#003399",
            "At Risk": "#f0a500",
            "Churned": "#cc0000"
        }

        fig_status = px.bar(
            status_df,
            x="Count",
            y="Status",
            orientation="h",
            text="Count",
            color="Status",
            color_discrete_map=color_map
        )
        fig_status.update_traces(
            textposition="outside",
            textfont=dict(size=11, color="#333333")
        )
        fig_status.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=5, r=5, t=10, b=5),
            xaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            yaxis=dict(showgrid=False, title=""),
            showlegend=False,
            height=300
        )
        st.plotly_chart(fig_status, use_container_width=True)

    # ---- CHART 3: Highest Avg Order Value ----
    with row1_right:
        st.markdown(
            "<div class='section-title'>💎 Highest Avg Order Value</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Customers who spend the most per order on average. "
            "Only customers with 2+ orders are shown for reliability. "
            "These are your premium customers — they buy in bulk or "
            "order expensive products. Target them for upselling "
            "and membership offers."
        )

        avg_by_customer = df.groupby("Customer Name").agg(
            Avg_Order=("Revenue", "mean"),
            Orders=("Order ID", "count")
        ).reset_index()
        avg_by_customer = avg_by_customer[avg_by_customer["Orders"] >= 2]
        avg_by_customer = avg_by_customer.sort_values(
            "Avg_Order", ascending=True
        ).tail(8)

        fig_high = px.bar(
            avg_by_customer,
            x="Avg_Order",
            y="Customer Name",
            orientation="h",
            text=avg_by_customer["Avg_Order"].apply(format_naira),
            color_discrete_sequence=["#003399"]
        )
        fig_high.update_traces(
            textposition="outside",
            textfont=dict(size=9, color="#333333")
        )
        fig_high.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=5, r=80, t=10, b=5),
            xaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            yaxis=dict(showgrid=False, title=""),
            height=300
        )
        st.plotly_chart(fig_high, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # ROW 3 — LTV by Area | Customer Distribution by Size
    # --------------------------------------------------------
    row2_left, row2_right = st.columns(2)

    # ---- CHART 4: LTV by Area ----
    with row2_left:
        st.markdown(
            "<div class='section-title'>📍 LTV Distribution by Area</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Lifetime Value (LTV) per delivery area — total revenue "
            "generated from all customers in each area. "
            "Tallest bars are your most valuable markets. "
            "Compare with order count to see if high-LTV areas "
            "are also high-frequency or just high-value per order."
        )

        ltv_by_area = df.groupby("Order Area/Location")[
            "Revenue"
        ].sum().reset_index()
        ltv_by_area.columns = ["Area", "LTV"]
        ltv_by_area = ltv_by_area.sort_values("LTV", ascending=False)

        fig_ltv = px.bar(
            ltv_by_area,
            x="Area",
            y="LTV",
            text=ltv_by_area["LTV"].apply(format_naira),
            color_discrete_sequence=["#003399"]
        )
        fig_ltv.update_traces(
            textposition="outside",
            textfont=dict(size=9, color="#333333")
        )
        fig_ltv.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=5, r=5, t=10, b=5),
            xaxis=dict(
                showgrid=False, title="",
                tickangle=-45, tickfont=dict(size=9)
            ),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            height=280
        )
        st.plotly_chart(fig_ltv, use_container_width=True)

    # ---- CHART 5: Customer Distribution by Order Size ----
    with row2_right:
        st.markdown(
            "<div class='section-title'>📦 Customer Distribution by Order Size</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Customers grouped by total volume purchased. "
            "Extra Large (10L+) are your biggest buyers — "
            "likely commercial or generator users. "
            "Small (<3L) are occasional buyers. "
            "Growing Extra Large segment means more high-value accounts."
        )

        customer_volume = df.groupby("Customer Name")[
            "Litre/Kg Sold"
        ].sum().reset_index()
        customer_volume.columns = ["Customer Name", "Total Volume"]

        def classify_size(vol):
            if vol >= 10:
                return "Extra Large (10L+)"
            elif vol >= 6:
                return "Large (6-10L)"
            elif vol >= 3:
                return "Medium (3-6L)"
            else:
                return "Small (< 3L)"

        customer_volume["Size Group"] = customer_volume["Total Volume"].apply(classify_size)
        size_order = ["Extra Large (10L+)", "Large (6-10L)", "Medium (3-6L)", "Small (< 3L)"]
        size_counts = customer_volume["Size Group"].value_counts().reindex(
            size_order
        ).fillna(0).reset_index()
        size_counts.columns = ["Size Group", "Count"]

        fig_size = go.Figure()
        fig_size.add_trace(go.Scatter(
            x=size_counts["Size Group"],
            y=size_counts["Count"],
            mode="markers+text",
            marker=dict(color="#003399", size=16),
            text=size_counts["Count"].astype(int),
            textposition="top center",
            textfont=dict(size=12, color="#333333")
        ))
        for _, row in size_counts.iterrows():
            fig_size.add_shape(
                type="line",
                x0=row["Size Group"], x1=row["Size Group"],
                y0=0, y1=row["Count"],
                line=dict(color="#003399", width=2)
            )
        fig_size.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=5, r=5, t=10, b=5),
            xaxis=dict(showgrid=False, title=""),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            height=280
        )
        st.plotly_chart(fig_size, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # CUSTOMER STATUS BY MONTH — Stacked Bar
    # --------------------------------------------------------
    st.markdown(
        "<div class='section-title'>📅 Customer Status by Month</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "How the active, at-risk, and churned customer counts "
        "have changed month by month. "
        "A growing blue section = improving retention. "
        "A growing red section = churn is accelerating — investigate. "
        "Use this to assess the impact of campaigns or pricing changes "
        "on customer behaviour over time."
    )

    monthly_status_rows = []
    for (year, month), month_df in df.groupby(["Year", "Month"]):
        month_end   = pd.Timestamp(year=int(year), month=int(month), day=1) + pd.offsets.MonthEnd(0)
        month_label = pd.Timestamp(year=int(year), month=int(month), day=1).strftime("%b %Y")

        customer_last = df[
            df["Date of Order"].dt.normalize() <= month_end
        ].groupby("Customer Name")["Date of Order"].max().reset_index()
        customer_last.columns = ["Customer Name", "Last Order"]
        customer_last["Days Since"] = (month_end - customer_last["Last Order"]).dt.days

        active  = (customer_last["Days Since"] <= 30).sum()
        at_risk = ((customer_last["Days Since"] > 30) & (customer_last["Days Since"] <= 60)).sum()
        churned = (customer_last["Days Since"] > 60).sum()

        monthly_status_rows.append({
            "Month":     month_label,
            "Year":      year,
            "Month Num": month,
            "Active":    active,
            "At Risk":   at_risk,
            "Churned":   churned
        })

    status_monthly_df = pd.DataFrame(monthly_status_rows).sort_values(["Year", "Month Num"])

    fig_status_monthly = go.Figure()
    fig_status_monthly.add_trace(go.Bar(
        name="Active",
        x=status_monthly_df["Month"],
        y=status_monthly_df["Active"],
        marker_color="#003399",
        text=status_monthly_df["Active"],
        textposition="inside",
        textfont=dict(color="white", size=11)
    ))
    fig_status_monthly.add_trace(go.Bar(
        name="At Risk",
        x=status_monthly_df["Month"],
        y=status_monthly_df["At Risk"],
        marker_color="#f0a500",
        text=status_monthly_df["At Risk"],
        textposition="inside",
        textfont=dict(color="white", size=11)
    ))
    fig_status_monthly.add_trace(go.Bar(
        name="Churned",
        x=status_monthly_df["Month"],
        y=status_monthly_df["Churned"],
        marker_color="#cc0000",
        text=status_monthly_df["Churned"],
        textposition="inside",
        textfont=dict(color="white", size=11)
    ))
    fig_status_monthly.update_layout(
        barmode="stack",
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis=dict(showgrid=False, title="", tickfont=dict(color="#333333")),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0",
                   title="Customers", tickfont=dict(color="#333333")),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=320
    )
    st.plotly_chart(fig_status_monthly, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # CHURN RATE BY AREA
    # --------------------------------------------------------
    st.markdown(
        "<div class='section-title'>📍 Customer Status by Area</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "Customer health broken down by delivery area. "
        "Left chart shows count of Active, At Risk, and Churned "
        "customers per area. "
        "Right chart shows churn rate % — the higher the bar "
        "the more customers GasFeel is losing in that area. "
        "Red bars (50%+) need immediate attention."
    )

    customer_area = df.groupby("Customer Name").agg(
        Last_Order=("Date of Order", "max"),
        Primary_Area=("Order Area/Location", lambda x: x.value_counts().index[0])
    ).reset_index()
    customer_area["Days Since"] = (today - customer_area["Last_Order"]).dt.days
    customer_area["Status"] = customer_area["Days Since"].apply(
        lambda x: "Active" if x <= 30 else ("At Risk" if x <= 60 else "Churned")
    )

    area_status = customer_area.groupby(
        ["Primary_Area", "Status"]
    ).size().reset_index()
    area_status.columns = ["Area", "Status", "Count"]

    area_totals = customer_area.groupby("Primary_Area").size().reset_index()
    area_totals.columns = ["Area", "Total"]

    area_churned = customer_area[
        customer_area["Status"] == "Churned"
    ].groupby("Primary_Area").size().reset_index()
    area_churned.columns = ["Area", "Churned"]

    area_churn_rate = area_totals.merge(area_churned, on="Area", how="left")
    area_churn_rate["Churned"] = area_churn_rate["Churned"].fillna(0)
    area_churn_rate["Churn Rate %"] = (
        area_churn_rate["Churned"] / area_churn_rate["Total"] * 100
    ).round(1)
    area_churn_rate = area_churn_rate.sort_values("Churn Rate %", ascending=False)

    col_churn1, col_churn2 = st.columns(2)

    with col_churn1:
        st.markdown(
            "<div class='section-title'>👥 Customer Count by Status per Area</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Stacked bar showing the composition of customers "
            "in each area. Blue = Active, Amber = At Risk, Red = Churned. "
            "Areas with tall red sections need re-engagement campaigns "
            "targeted specifically at those locations."
        )

        area_pivot = area_status.pivot(
            index="Area", columns="Status", values="Count"
        ).fillna(0).reset_index()

        fig_area_stack = go.Figure()
        if "Active" in area_pivot.columns:
            fig_area_stack.add_trace(go.Bar(
                name="Active",
                x=area_pivot["Area"],
                y=area_pivot["Active"],
                marker_color="#003399",
                text=area_pivot["Active"].astype(int),
                textposition="inside",
                textfont=dict(color="white", size=10)
            ))
        if "At Risk" in area_pivot.columns:
            fig_area_stack.add_trace(go.Bar(
                name="At Risk",
                x=area_pivot["Area"],
                y=area_pivot["At Risk"],
                marker_color="#f0a500",
                text=area_pivot["At Risk"].astype(int),
                textposition="inside",
                textfont=dict(color="white", size=10)
            ))
        if "Churned" in area_pivot.columns:
            fig_area_stack.add_trace(go.Bar(
                name="Churned",
                x=area_pivot["Area"],
                y=area_pivot["Churned"],
                marker_color="#cc0000",
                text=area_pivot["Churned"].astype(int),
                textposition="inside",
                textfont=dict(color="white", size=10)
            ))
        fig_area_stack.update_layout(
            barmode="stack",
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=10, r=10, t=20, b=10),
            xaxis=dict(
                showgrid=False, title="",
                tickangle=-45, tickfont=dict(color="#333333", size=9)
            ),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0",
                       title="Customers", tickfont=dict(color="#333333")),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=350
        )
        st.plotly_chart(fig_area_stack, use_container_width=True)

    with col_churn2:
        st.markdown(
            "<div class='section-title'>🔴 Churn Rate % by Area</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Percentage of customers lost per area. "
            "Red = 50%+ churn (critical). "
            "Amber = 30-50% (concerning). "
            "Blue = below 30% (healthy). "
            "Focus re-engagement efforts on red and amber areas first."
        )

        area_churn_rate["Color"] = area_churn_rate["Churn Rate %"].apply(
            lambda x: "#cc0000" if x >= 50 else ("#f0a500" if x >= 30 else "#003399")
        )

        fig_churn = go.Figure()
        fig_churn.add_trace(go.Bar(
            x=area_churn_rate["Churn Rate %"],
            y=area_churn_rate["Area"],
            orientation="h",
            marker_color=area_churn_rate["Color"],
            text=area_churn_rate["Churn Rate %"].apply(lambda x: f"{x:.1f}%"),
            textposition="outside",
            textfont=dict(size=10, color="#333333")
        ))
        fig_churn.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=10, r=60, t=20, b=10),
            xaxis=dict(
                showgrid=True, gridcolor="#f0f0f0",
                title="Churn Rate %", tickfont=dict(color="#333333"),
                range=[0, max(area_churn_rate["Churn Rate %"]) * 1.2]
            ),
            yaxis=dict(showgrid=False, title="", tickfont=dict(color="#333333")),
            height=350
        )
        st.plotly_chart(fig_churn, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- Area Churn Summary Table ----
    st.markdown(
        "<div class='section-title'>📋 Area Churn Summary Table</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "Full breakdown of customer health per area. "
        "Sort by Churn Rate % to find the most at-risk areas. "
        "Retention Rate % = Active customers ÷ Total customers per area."
    )

    area_active = customer_area[
        customer_area["Status"] == "Active"
    ].groupby("Primary_Area").size().reset_index()
    area_active.columns = ["Area", "Active"]

    area_risk = customer_area[
        customer_area["Status"] == "At Risk"
    ].groupby("Primary_Area").size().reset_index()
    area_risk.columns = ["Area", "At Risk"]

    area_summary = area_totals.merge(area_active, on="Area", how="left")
    area_summary = area_summary.merge(area_risk, on="Area", how="left")
    area_summary = area_summary.merge(area_churned, on="Area", how="left")
    area_summary["Active"]   = area_summary["Active"].fillna(0).astype(int)
    area_summary["At Risk"]  = area_summary["At Risk"].fillna(0).astype(int)
    area_summary["Churned"]  = area_summary["Churned"].fillna(0).astype(int)
    area_summary["Churn Rate %"] = (
        area_summary["Churned"] / area_summary["Total"] * 100
    ).round(1).astype(str) + "%"
    area_summary["Retention Rate %"] = (
        area_summary["Active"] / area_summary["Total"] * 100
    ).round(1).astype(str) + "%"
    area_summary = area_summary.rename(
        columns={"Primary_Area": "Area", "Total": "Total Customers"}
    )
    area_summary = area_summary.sort_values("Churned", ascending=False)

    st.dataframe(
        area_summary[[
            "Area", "Total Customers", "Active",
            "At Risk", "Churned", "Churn Rate %", "Retention Rate %"
        ]],
        use_container_width=True,
        hide_index=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # CUSTOMER LISTS BY STATUS
    # --------------------------------------------------------
    st.markdown(
        "<div class='section-title'>📋 Customer List by Status</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "Full list of every customer grouped by their current status. "
        "Active = safe, no action needed. "
        "At Risk = call or message them now before they churn. "
        "Churned = re-engagement campaign needed — offer incentive to return. "
        "Sorted by days since last order so most urgent shows first."
    )

    customer_status_df = df.groupby("Customer Name").agg(
        Last_Order=("Date of Order", "max"),
        Total_Orders=("Order ID", "count"),
        Total_Revenue=("Revenue", "sum")
    ).reset_index()
    customer_status_df["Days Since Order"] = (
        today - customer_status_df["Last_Order"]
    ).dt.days
    customer_status_df["Status"] = customer_status_df["Days Since Order"].apply(
        lambda x: "Active" if x <= 30 else ("At Risk" if x <= 60 else "Churned")
    )
    customer_status_df["Last Order"]  = customer_status_df["Last_Order"].dt.strftime("%d %b %Y")
    customer_status_df["Revenue"]     = customer_status_df["Total_Revenue"].apply(format_naira)
    customer_status_df = customer_status_df.rename(columns={
        "Customer Name": "Customer",
        "Total_Orders":  "Orders",
        "Days Since Order": "Days Since Last Order"
    })[["Customer", "Status", "Last Order", "Days Since Last Order", "Orders", "Revenue"]]

    col_active, col_risk, col_churned = st.columns(3)

    with col_active:
        st.markdown("""
            <div style='background:#efffef;border-left:4px solid #00aa44;
                        border-radius:10px;padding:12px 16px;margin-bottom:12px;'>
                <span style='color:#006622;font-size:12px;font-weight:800;
                             text-transform:uppercase;'>✅ Active Customers</span>
            </div>
        """, unsafe_allow_html=True)
        active_list = customer_status_df[
            customer_status_df["Status"] == "Active"
        ].sort_values("Days Since Last Order")
        st.dataframe(
            active_list[[
                "Customer", "Last Order",
                "Days Since Last Order", "Orders", "Revenue"
            ]],
            use_container_width=True, hide_index=True, height=400
        )

    with col_risk:
        st.markdown("""
            <div style='background:#fff8e6;border-left:4px solid #f0a500;
                        border-radius:10px;padding:12px 16px;margin-bottom:12px;'>
                <span style='color:#b37a00;font-size:12px;font-weight:800;
                             text-transform:uppercase;'>⚠️ At Risk Customers</span>
            </div>
        """, unsafe_allow_html=True)
        risk_list = customer_status_df[
            customer_status_df["Status"] == "At Risk"
        ].sort_values("Days Since Last Order")
        st.dataframe(
            risk_list[[
                "Customer", "Last Order",
                "Days Since Last Order", "Orders", "Revenue"
            ]],
            use_container_width=True, hide_index=True, height=400
        )

    with col_churned:
        st.markdown("""
            <div style='background:#fff0f0;border-left:4px solid #cc0000;
                        border-radius:10px;padding:12px 16px;margin-bottom:12px;'>
                <span style='color:#990000;font-size:12px;font-weight:800;
                             text-transform:uppercase;'>❌ Churned Customers</span>
            </div>
        """, unsafe_allow_html=True)
        churned_list = customer_status_df[
            customer_status_df["Status"] == "Churned"
        ].sort_values("Days Since Last Order", ascending=False)
        st.dataframe(
            churned_list[[
                "Customer", "Last Order",
                "Days Since Last Order", "Orders", "Revenue"
            ]],
            use_container_width=True, hide_index=True, height=400
        )