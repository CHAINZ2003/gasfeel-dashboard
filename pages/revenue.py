# ============================================================
# REVENUE TAB — GasFeel Dashboard
# Shows Revenue & Growth Analysis matching the Excel tab.
# Charts: Revenue by day, by area, by product, by station.
# Called from app.py with filtered_df as input.
# ============================================================

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


# ============================================================
# HELPER — FORMAT NAIRA VALUES
# Converts raw numbers to readable ₦ format.
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
# Renders a single white metric card with blue styling.
# ============================================================

def kpi_card(label, value, color="kpi-value"):
    st.markdown(f"""
        <div class='kpi-card'>
            <div class='kpi-label'>{label}</div>
            <div class='{color}'>{value}</div>
        </div>
    """, unsafe_allow_html=True)


# ============================================================
# MAIN RENDER FUNCTION — REVENUE TAB
# ============================================================

def render_revenue(df):

    # --------------------------------------------------------
    # CALCULATE TOP-LINE REVENUE KPIs
    # These 6 metrics sit at the left side of the tab.
    # --------------------------------------------------------

    # Total GMV — sum of all customer payments
    total_gmv = df["Revenue (Total Customer Payment)"].sum()

    # Total Revenue (same as GMV in this context)
    total_revenue = df["Revenue"].sum()

    # Total Delivery Cost paid to riders
    total_delivery_cost = df["Delivery Cost (how much we paid to the Rider)"].sum()

    # Total Profit = Revenue - COGS - Delivery Cost
    total_profit = df["Profit"].sum()

    # Profit Margin = Profit / Revenue × 100
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

    # Delivery Profit = Delivery Fee collected - Delivery Cost paid
    total_delivery_fee = df["Delivery Fee (Amount we Collected from the customer)"].sum()
    delivery_profit = total_delivery_fee - total_delivery_cost

    # --------------------------------------------------------
    # LAYOUT — LEFT COLUMN (KPIs) + RIGHT COLUMN (Charts)
    # --------------------------------------------------------
    col_kpis, col_charts = st.columns([1, 2.5])

    # --------------------------------------------------------
    # LEFT COLUMN — KPI CARDS
    # --------------------------------------------------------
    with col_kpis:
        st.markdown("<div class='section-title'>💰 Revenue Summary</div>", unsafe_allow_html=True)

        kpi_card("GMV", format_naira(total_gmv))
        kpi_card("Revenue", format_naira(total_revenue))
        kpi_card("Delivery Cost", format_naira(total_delivery_cost))
        kpi_card("Profit", format_naira(total_profit))

        # Profit margin with colour — green if positive, red if negative
        margin_color = "kpi-positive" if profit_margin >= 0 else "kpi-negative"
        margin_str = f"▲{profit_margin:.1f}%" if profit_margin >= 0 else f"▼{abs(profit_margin):.1f}%"
        pm_delta = profit_margin if profit_margin >= 0 else -abs(profit_margin)
        st.metric(
            label="Profit Margin",
            value="",
            delta=f"{pm_delta:.1f}%",
            delta_color="normal"
        )

        kpi_card("Delivery Profit", format_naira(delivery_profit))

    # --------------------------------------------------------
    # RIGHT COLUMN — CHARTS (2x2 grid)
    # --------------------------------------------------------
    with col_charts:

        # --- ROW 1: Revenue by Day | Revenue by Product ---
        row1_left, row1_right = st.columns(2)

        # ---- CHART 1: Revenue by Day of Week ----
        with row1_left:
            st.markdown("<div class='section-title'>📅 Revenue by Day</div>", unsafe_allow_html=True)

            # Group revenue by day, order Sun-Sat
            day_order = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

            # Map short day names to full names if needed
            day_map = {"Sun": "Sunday", "Mon": "Monday", "Tue": "Tuesday",
                       "Wed": "Wednesday", "Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday"}
            df["Full Day"] = df["Day of the Week"].map(day_map).fillna(df["Day of the Week"])

            revenue_by_day = df.groupby("Full Day")["Revenue (Total Customer Payment)"].sum().reset_index()
            revenue_by_day["Day Order"] = revenue_by_day["Full Day"].apply(
                lambda x: day_order.index(x) if x in day_order else 99
            )
            revenue_by_day = revenue_by_day.sort_values("Day Order")

            fig_day = go.Figure()
            fig_day.add_trace(go.Scatter(
                x=revenue_by_day["Full Day"],
                y=revenue_by_day["Revenue (Total Customer Payment)"],
                mode="markers+lines+text",
                marker=dict(color="#003399", size=12),
                line=dict(color="#003399", width=2),
                text=revenue_by_day["Revenue (Total Customer Payment)"].apply(format_naira),
                textposition="top center",
                textfont=dict(size=10)
            ))
            fig_day.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=10, r=30, t=20, b=10),
                xaxis=dict(showgrid=False, title=""),
                yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
                height=220
            )
            st.plotly_chart(fig_day, use_container_width=True)

        # ---- CHART 2: Revenue by Product Type ----
        with row1_right:
            st.markdown("<div class='section-title'>🛢️ Revenue by Product</div>", unsafe_allow_html=True)

            revenue_by_product = df.groupby("Order Type")["Revenue (Total Customer Payment)"].sum().reset_index()

            fig_product = px.pie(
                revenue_by_product,
                names="Order Type",
                values="Revenue (Total Customer Payment)",
                hole=0.55,
                color_discrete_sequence=["#003399", "#6699ff", "#ccd9ff"]
            )
            fig_product.update_traces(
                textinfo="label+percent",
                textfont_size=11
            )
            fig_product.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=10, r=30, t=20, b=10),
                showlegend=True,
                legend=dict(orientation="v", x=1, y=0.5),
                height=220
            )
            st.plotly_chart(fig_product, use_container_width=True)

        # --- ROW 2: Revenue by Area | Revenue by Station ---
        row2_left, row2_right = st.columns(2)

        # ---- CHART 3: Revenue by Area/Location ----
        with row2_left:
            st.markdown("<div class='section-title'>📍 Revenue by Area</div>", unsafe_allow_html=True)

            revenue_by_area = df.groupby("Order Area/Location")[
                "Revenue (Total Customer Payment)"
            ].sum().reset_index().sort_values("Revenue (Total Customer Payment)", ascending=False)

            fig_area = px.bar(
                revenue_by_area,
                x="Order Area/Location",
                y="Revenue (Total Customer Payment)",
                text=revenue_by_area["Revenue (Total Customer Payment)"].apply(format_naira),
                color_discrete_sequence=["#003399"]
            )
            fig_area.update_traces(textposition="outside", textfont_size=9)
            fig_area.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=10, r=30, t=20, b=10),
                xaxis=dict(showgrid=False, title="", tickangle=-45, tickfont=dict(size=9)),
                yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
                height=250
            )
            st.plotly_chart(fig_area, use_container_width=True)

        # ---- CHART 4: Revenue by Station ----
        with row2_right:
            st.markdown("<div class='section-title'>🏪 Revenue by Station</div>", unsafe_allow_html=True)

            revenue_by_station = df.groupby("Station")[
                "Revenue (Total Customer Payment)"
            ].sum().reset_index().sort_values("Revenue (Total Customer Payment)", ascending=False)

            fig_station = px.bar(
                revenue_by_station,
                x="Revenue (Total Customer Payment)",
                y="Station",
                orientation="h",
                text=revenue_by_station["Revenue (Total Customer Payment)"].apply(format_naira),
                color_discrete_sequence=["#003399"]
            )
            fig_station.update_traces(textposition="outside", textfont_size=10)
            fig_station.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=10, r=30, t=20, b=10),
                xaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
                yaxis=dict(showgrid=False, title=""),
                height=250
            )
            st.plotly_chart(fig_station, use_container_width=True)
            # --------------------------------------------------------
    # CHART — Product Revenue Contribution by Month
    # Shows how each product type (Engine Oil, Gas LPG,
    # Petrol PMS) contributes to total revenue each month.
    # Reveals product mix trends over time.
    # --------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>📅 Product Revenue by Month</div>", unsafe_allow_html=True)

    # Group revenue by month and product type
    product_monthly = df.groupby(
        ["Year", "Month", "Month Name", "Order Type"]
    )["Revenue"].sum().reset_index()

    # Create proper month label for x-axis
    product_monthly["Month Label"] = product_monthly.apply(
        lambda r: pd.Timestamp(
            year=int(r["Year"]), month=int(r["Month"]), day=1
        ).strftime("%b %Y"), axis=1
    )
    product_monthly = product_monthly.sort_values(["Year", "Month"])

    # Get unique product types
    product_types = product_monthly["Order Type"].unique()

    # Assign colours per product type
    color_map = {
        "Petrol (Pms)": "#003399",
        "Gas (Lpg)": "#6699ff",
        "Engine Oil": "#ccd9ff",
    }

    fig_product_monthly = go.Figure()

    for product in product_types:
        product_data = product_monthly[product_monthly["Order Type"] == product]
        color = color_map.get(product, "#003399")

        fig_product_monthly.add_trace(go.Bar(
            name=product,
            x=product_data["Month Label"],
            y=product_data["Revenue"],
            marker_color=color,
            text=product_data["Revenue"].apply(format_naira),
            textposition="inside",
            textfont=dict(color="white", size=10, family="Segoe UI")
        ))

    fig_product_monthly.update_layout(
        barmode="stack",
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis=dict(showgrid=False, title="", tickfont=dict(color="#333333")),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title="Revenue (₦)", tickfont=dict(color="#333333")),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=320
    )

    st.plotly_chart(fig_product_monthly, use_container_width=True)
        