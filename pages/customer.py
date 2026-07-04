# ============================================================
# CUSTOMER TAB — GasFeel Dashboard
# Shows Customer Analytics matching the Excel tab.
# KPIs: Total Customers, Active, Churned, AOV, Profit/Customer
# Charts: Top customers, Customer status, LTV by area,
#         Customer distribution by order size, High-value customers
# Called from app.py with filtered_df as input.
# ============================================================

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import timedelta


# ============================================================
# HELPER — FORMAT NAIRA VALUES
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
# ============================================================

def kpi_card(label, value, color="kpi-value"):
    st.markdown(f"""
        <div class='kpi-card'>
            <div class='kpi-label'>{label}</div>
            <div class='{color}'>{value}</div>
        </div>
    """, unsafe_allow_html=True)


# ============================================================
# MAIN RENDER FUNCTION — CUSTOMER TAB
# ============================================================

def render_customer(df):

    # --------------------------------------------------------
    # CALCULATE CUSTOMER STATUS
    # Active = ordered in last 30 days
    # At Risk = last order between 31-60 days ago
    # Churned = no order in over 60 days
    # --------------------------------------------------------
    today = pd.Timestamp.now().normalize()

    # Get last order date per customer
    last_order = df.groupby("Customer Name")["Date of Order"].max().reset_index()
    last_order.columns = ["Customer Name", "Last Order Date"]

    # Calculate days since last order
    last_order["Days Since Order"] = (today - last_order["Last Order Date"]).dt.days

    # Assign status based on recency
    def assign_status(days):
        if days <= 30:
            return "Active"
        elif days <= 60:
            return "At Risk"
        else:
            return "Churned"

    last_order["Status"] = last_order["Days Since Order"].apply(assign_status)

    # Count each status
    status_counts = last_order["Status"].value_counts()
    total_customers = len(last_order)
    active_count = status_counts.get("Active", 0)
    at_risk_count = status_counts.get("At Risk", 0)
    churned_count = status_counts.get("Churned", 0)

    # --------------------------------------------------------
    # CALCULATE TOP-LINE CUSTOMER KPIs
    # --------------------------------------------------------

    # Average order value = total revenue / total orders
    total_revenue = df["Revenue (Total Customer Payment)"].sum()
    total_orders = len(df)
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

    # Profit per customer = total profit / unique customers
    total_profit = df["Profit"].sum()
    profit_per_customer = total_profit / total_customers if total_customers > 0 else 0

    # --------------------------------------------------------
    # TOP-LINE KPI ROW — 4 cards across
    # --------------------------------------------------------
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        kpi_card("Total Customers", f"{total_customers:,}")
    with k2:
        # Show active count with churned below it
        st.markdown(f"""
            <div class='kpi-card'>
                <div class='kpi-label'>Active Customers</div>
                <div class='kpi-value'>{active_count}</div>
                <div class='kpi-label' style='margin-top:6px;'>Churned: <b>{churned_count}</b></div>
            </div>
        """, unsafe_allow_html=True)
    with k3:
        kpi_card("Avg Order Value", format_naira(avg_order_value))
    with k4:
        kpi_card("Profit / Customer", format_naira(profit_per_customer))

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # ROW 2 — TOP CUSTOMERS | CUSTOMER STATUS | HIGH VALUE
    # --------------------------------------------------------
    row1_left, row1_mid, row1_right = st.columns(3)

    # ---- CHART 1: Top Customers by Revenue ----
    with row1_left:
        st.markdown("<div class='section-title'>🏆 Top Customers by Revenue</div>", unsafe_allow_html=True)

        # Sum revenue per customer, take top 8
        top_customers = df.groupby("Customer Name")[
            "Revenue (Total Customer Payment)"
        ].sum().reset_index().sort_values(
            "Revenue (Total Customer Payment)", ascending=True
        ).tail(8)

        fig_top = px.bar(
            top_customers,
            x="Revenue (Total Customer Payment)",
            y="Customer Name",
            orientation="h",
            text=top_customers["Revenue (Total Customer Payment)"].apply(format_naira),
            color_discrete_sequence=["#003399"]
        )
        fig_top.update_traces(textposition="outside", textfont_size=9)
        fig_top.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=10, r=30, t=20, b=10),
            xaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            yaxis=dict(showgrid=False, title=""),
            height=280
        )
        st.plotly_chart(fig_top, use_container_width=True)

    # ---- CHART 2: Customer Status Breakdown ----
    with row1_mid:
        st.markdown("<div class='section-title'>📊 Customer Status</div>", unsafe_allow_html=True)

        status_df = pd.DataFrame({
            "Status": ["Active", "At Risk", "Churned"],
            "Count": [active_count, at_risk_count, churned_count]
        })

        # Colour each status segment distinctly
        color_map = {
            "Active": "#003399",
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
        fig_status.update_traces(textposition="outside", textfont_size=11)
        fig_status.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=10, r=30, t=20, b=10),
            xaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            yaxis=dict(showgrid=False, title=""),
            showlegend=False,
            height=280
        )
        st.plotly_chart(fig_status, use_container_width=True)

    # ---- CHART 3: Customers Who Place Higher Value Orders ----
    with row1_right:
        st.markdown("<div class='section-title'>💎 Highest Avg Order Value</div>", unsafe_allow_html=True)

        # Average order value per customer
        avg_by_customer = df.groupby("Customer Name").agg(
            Avg_Order=("Revenue (Total Customer Payment)", "mean"),
            Orders=("Order ID", "count")
        ).reset_index()

        # Only show customers with more than 1 order for reliability
        avg_by_customer = avg_by_customer[avg_by_customer["Orders"] >= 2]
        avg_by_customer = avg_by_customer.sort_values("Avg_Order", ascending=True).tail(8)

        fig_high = px.bar(
            avg_by_customer,
            x="Avg_Order",
            y="Customer Name",
            orientation="h",
            text=avg_by_customer["Avg_Order"].apply(format_naira),
            color_discrete_sequence=["#003399"]
        )
        fig_high.update_traces(textposition="outside", textfont_size=9)
        fig_high.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=10, r=30, t=20, b=10),
            xaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            yaxis=dict(showgrid=False, title=""),
            height=280
        )
        st.plotly_chart(fig_high, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # ROW 3 — LTV BY AREA | CUSTOMER DISTRIBUTION BY SIZE
    # --------------------------------------------------------
    row2_left, row2_right = st.columns(2)

    # ---- CHART 4: LTV Distribution by Area ----
    with row2_left:
        st.markdown("<div class='section-title'>📍 LTV Distribution by Area</div>", unsafe_allow_html=True)

        # LTV = total revenue per customer grouped by their area
        ltv_by_area = df.groupby("Order Area/Location")[
            "Revenue (Total Customer Payment)"
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
        fig_ltv.update_traces(textposition="outside", textfont_size=9)
        fig_ltv.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=10, r=30, t=20, b=10),
            xaxis=dict(showgrid=False, title="", tickangle=-45, tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            height=260
        )
        st.plotly_chart(fig_ltv, use_container_width=True)

    # ---- CHART 5: Customer Distribution by Order Size ----
    with row2_right:
        st.markdown("<div class='section-title'>📦 Customer Distribution by Order Size</div>", unsafe_allow_html=True)

        # Classify each customer by their total litres/kg purchased
        # Extra Large = 10+ litres, Large = 6-10, Medium = 3-6, Small = under 3
        customer_volume = df.groupby("Customer Name")["Litre/Kg Sold"].sum().reset_index()
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
        size_counts = customer_volume["Size Group"].value_counts().reindex(size_order).fillna(0).reset_index()
        size_counts.columns = ["Size Group", "Count"]

        fig_size = go.Figure()
        fig_size.add_trace(go.Scatter(
            x=size_counts["Size Group"],
            y=size_counts["Count"],
            mode="markers+text",
            marker=dict(color="#003399", size=16),
            text=size_counts["Count"].astype(int),
            textposition="top center",
            textfont=dict(size=12)
        ))
        # Add vertical lines for lollipop effect
        for _, row in size_counts.iterrows():
            fig_size.add_shape(
                type="line",
                x0=row["Size Group"], x1=row["Size Group"],
                y0=0, y1=row["Count"],
                line=dict(color="#003399", width=2)
            )
        fig_size.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=10, r=30, t=20, b=10),
            xaxis=dict(showgrid=False, title=""),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            height=260
        )
        st.plotly_chart(fig_size, use_container_width=True)
    
    # --------------------------------------------------------
    # CHART — Customer Status by Month (Stacked Bar)
    # Shows how Active, At Risk, and Churned counts change
    # across each month — reveals retention trends over time.
    # --------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>📅 Customer Status by Month</div>", unsafe_allow_html=True)

    # Build monthly status breakdown
    # For each month, classify each customer based on their
    # last order date relative to the end of that month
    monthly_status_rows = []

    for (year, month), month_df in df.groupby(["Year", "Month"]):
        month_end = pd.Timestamp(year=int(year), month=int(month), day=1) + pd.offsets.MonthEnd(0)
        month_label = pd.Timestamp(year=int(year), month=int(month), day=1).strftime("%b %Y")

        # Get last order date per customer up to end of this month
        customer_last = df[
            df["Date of Order"].dt.normalize() <= month_end
        ].groupby("Customer Name")["Date of Order"].max().reset_index()
        customer_last.columns = ["Customer Name", "Last Order"]
        customer_last["Days Since"] = (month_end - customer_last["Last Order"]).dt.days

        # Classify each customer for this month
        active = (customer_last["Days Since"] <= 30).sum()
        at_risk = ((customer_last["Days Since"] > 30) & (customer_last["Days Since"] <= 60)).sum()
        churned = (customer_last["Days Since"] > 60).sum()

        monthly_status_rows.append({
            "Month": month_label,
            "Year": year,
            "Month Num": month,
            "Active": active,
            "At Risk": at_risk,
            "Churned": churned
        })

    status_monthly_df = pd.DataFrame(monthly_status_rows).sort_values(["Year", "Month Num"])

    fig_status_monthly = go.Figure()

    # Active — dark blue bar
    fig_status_monthly.add_trace(go.Bar(
        name="Active",
        x=status_monthly_df["Month"],
        y=status_monthly_df["Active"],
        marker_color="#003399",
        text=status_monthly_df["Active"],
        textposition="inside",
        textfont=dict(color="white", size=11, family="Segoe UI")
    ))

    # At Risk — amber bar
    fig_status_monthly.add_trace(go.Bar(
        name="At Risk",
        x=status_monthly_df["Month"],
        y=status_monthly_df["At Risk"],
        marker_color="#f0a500",
        text=status_monthly_df["At Risk"],
        textposition="inside",
        textfont=dict(color="white", size=11, family="Segoe UI")
    ))

    # Churned — red bar
    fig_status_monthly.add_trace(go.Bar(
        name="Churned",
        x=status_monthly_df["Month"],
        y=status_monthly_df["Churned"],
        marker_color="#cc0000",
        text=status_monthly_df["Churned"],
        textposition="inside",
        textfont=dict(color="white", size=11, family="Segoe UI")
    ))

    fig_status_monthly.update_layout(
        barmode="stack",
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis=dict(showgrid=False, title="", tickfont=dict(color="#333333")),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title="Customers", tickfont=dict(color="#333333")),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=320
    )

    st.plotly_chart(fig_status_monthly, use_container_width=True)
