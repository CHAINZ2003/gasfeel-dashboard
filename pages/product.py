# ============================================================
# PRODUCT TAB — GasFeel Dashboard
# Shows Product Performance matching the Excel tab.
# KPIs: Total Orders, Quantity, Avg Order Value, Avg Litres
# Charts: Volume by day, demand by area, reorder rate,
#         avg orders per customer by week, product revenue
# Called from app.py with filtered_df as input.
# ============================================================

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


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
# MAIN RENDER FUNCTION — PRODUCT TAB
# ============================================================

def render_product(df):

    # --------------------------------------------------------
    # CALCULATE TOP-LINE PRODUCT KPIs
    # --------------------------------------------------------

    # Total number of orders
    total_orders = len(df)

    # Total quantity sold in litres/kg
    total_quantity = df["Litre/Kg Sold"].sum()

    # Average order value = total revenue / total orders
    avg_order_value = df["Revenue (Total Customer Payment)"].sum() / total_orders if total_orders > 0 else 0

    # Average litres or kg per order
    avg_litres_per_order = total_quantity / total_orders if total_orders > 0 else 0

    # --------------------------------------------------------
    # LAYOUT — TOP KPI ROW (4 cards across)
    # --------------------------------------------------------
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        kpi_card("Total Orders", f"{total_orders:,}")
    with k2:
        kpi_card("Total Quantity", f"{total_quantity:,.2f}")
    with k3:
        kpi_card("Avg Order Value", format_naira(avg_order_value))
    with k4:
        kpi_card("Avg Litres/Kg per Order", f"{avg_litres_per_order:.1f}")

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # ROW 2 — VOLUME BY DAY | DEMAND BY AREA
    # --------------------------------------------------------
    row1_left, row1_right = st.columns(2)

    # ---- CHART 1: Product Volume by Day of Week ----
    with row1_left:
        st.markdown("<div class='section-title'>📅 Product Volume by Day</div>", unsafe_allow_html=True)

        # Map short day names to full names for display
        day_order = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        day_map = {
            "Sun": "Sunday", "Mon": "Monday", "Tue": "Tuesday",
            "Wed": "Wednesday", "Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday"
        }
        df["Full Day"] = df["Day of the Week"].map(day_map).fillna(df["Day of the Week"])

        # Group total litres/kg sold by day
        volume_by_day = df.groupby("Full Day")["Litre/Kg Sold"].sum().reset_index()
        volume_by_day["Day Order"] = volume_by_day["Full Day"].apply(
            lambda x: day_order.index(x) if x in day_order else 99
        )
        volume_by_day = volume_by_day.sort_values("Day Order")

        fig_vol = go.Figure()
        fig_vol.add_trace(go.Scatter(
            x=volume_by_day["Full Day"],
            y=volume_by_day["Litre/Kg Sold"],
            mode="lines+markers+text",
            marker=dict(color="#003399", size=10),
            line=dict(color="#003399", width=2),
            text=volume_by_day["Litre/Kg Sold"].apply(lambda x: f"{x:,.1f}"),
            textposition="top center",
            textfont=dict(size=10)
        ))
        fig_vol.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=10, r=30, t=20, b=10),
            xaxis=dict(showgrid=False, title=""),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            height=230
        )
        st.plotly_chart(fig_vol, use_container_width=True)

    # ---- CHART 2: Product Demand by Area ----
    with row1_right:
        st.markdown("<div class='section-title'>📍 Product Demand by Area</div>", unsafe_allow_html=True)

        # Count orders per area to show demand
        demand_by_area = df.groupby("Order Area/Location")["Order ID"].count().reset_index()
        demand_by_area.columns = ["Area", "Orders"]
        demand_by_area = demand_by_area.sort_values("Orders", ascending=False)

        fig_demand = px.bar(
            demand_by_area,
            x="Area",
            y="Orders",
            text="Orders",
            color_discrete_sequence=["#003399"]
        )
        fig_demand.update_traces(textposition="outside", textfont_size=9)
        fig_demand.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=10, r=30, t=20, b=10),
            xaxis=dict(showgrid=False, title="", tickangle=-45, tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            height=230
        )
        st.plotly_chart(fig_demand, use_container_width=True)

    # --------------------------------------------------------
    # ROW 3 — PRODUCT REVENUE DONUT | AVG ORDERS/CUSTOMER | REORDER RATE
    # --------------------------------------------------------
    row2_left, row2_mid, row2_right = st.columns(3)

    # ---- CHART 3: Revenue by Product Type (Donut) ----
    with row2_left:
        st.markdown("<div class='section-title'>🛢️ Revenue by Product Type</div>", unsafe_allow_html=True)

        revenue_by_product = df.groupby("Order Type")[
            "Revenue (Total Customer Payment)"
        ].sum().reset_index()

        fig_donut = px.pie(
            revenue_by_product,
            names="Order Type",
            values="Revenue (Total Customer Payment)",
            hole=0.55,
            color_discrete_sequence=["#003399", "#6699ff", "#ccd9ff"]
        )
        fig_donut.update_traces(
            textinfo="label+percent",
            textfont_size=10
        )
        fig_donut.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=10, r=30, t=20, b=10),
            showlegend=False,
            height=250
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    # ---- CHART 4: Average Orders per Customer by Week ----
    with row2_mid:
        st.markdown("<div class='section-title'>👤 Avg Orders/Customer by Week</div>", unsafe_allow_html=True)

        # Count orders per customer per week, then average per week
        orders_per_week = df.groupby(["Week", "Customer Name"])["Order ID"].count().reset_index()
        avg_orders_per_week = orders_per_week.groupby("Week")["Order ID"].mean().reset_index()
        avg_orders_per_week.columns = ["Week", "Avg Orders"]
        avg_orders_per_week = avg_orders_per_week.sort_values("Week").tail(8)
        avg_orders_per_week["Week Label"] = "WK" + avg_orders_per_week["Week"].astype(str)

        fig_avg = go.Figure()
        fig_avg.add_trace(go.Scatter(
            x=avg_orders_per_week["Week Label"],
            y=avg_orders_per_week["Avg Orders"],
            mode="markers+text",
            marker=dict(color="#003399", size=14),
            text=avg_orders_per_week["Avg Orders"].apply(lambda x: f"{x:.1f}"),
            textposition="top center",
            textfont=dict(size=11)
        ))
        # Add vertical lines from x-axis to each marker (lollipop style)
        for _, row in avg_orders_per_week.iterrows():
            fig_avg.add_shape(
                type="line",
                x0=row["Week Label"], x1=row["Week Label"],
                y0=0, y1=row["Avg Orders"],
                line=dict(color="#003399", width=2)
            )
        fig_avg.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=10, r=30, t=20, b=10),
            xaxis=dict(showgrid=False, title=""),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            height=250
        )
        st.plotly_chart(fig_avg, use_container_width=True)

    # ---- CHART 5: Reorder Rate % by Month ----
    with row2_right:
        st.markdown("<div class='section-title'>🔄 Reorder Rate % by Month</div>", unsafe_allow_html=True)

        # Reorder rate = customers who ordered more than once that month
        # divided by total unique customers that month × 100
        monthly_reorder = []
        for (year, month), month_df in df.groupby(["Year", "Month"]):
            customer_counts = month_df.groupby("Customer Name")["Order ID"].count()
            repeat = (customer_counts > 1).sum()
            total = customer_counts.count()
            rate = (repeat / total * 100) if total > 0 else 0
            month_name = month_df["Month Name"].iloc[0]
            monthly_reorder.append({
                "Month": month_name,
                "Year": year,
                "Month Num": month,
                "Reorder Rate": round(rate, 1)
            })

        reorder_df = pd.DataFrame(monthly_reorder).sort_values(["Year", "Month Num"])

        fig_reorder = px.bar(
            reorder_df,
            x="Reorder Rate",
            y="Month",
            orientation="h",
            text=reorder_df["Reorder Rate"].apply(lambda x: f"{x:.0f}%"),
            color_discrete_sequence=["#003399"]
        )
        fig_reorder.update_traces(textposition="outside", textfont_size=10)
        fig_reorder.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=10, r=30, t=20, b=10),
            xaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            yaxis=dict(showgrid=False, title="", autorange="reversed"),
            height=250
        )
        st.plotly_chart(fig_reorder, use_container_width=True)