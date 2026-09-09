# ============================================================
# REVENUE TAB — GasFeel Dashboard
# Shows Revenue & Growth Analysis.
# Charts: Revenue by day, by area, by product, by station,
# and product revenue by month stacked bar.
# All charts include descriptions for team readability.
# ============================================================

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


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
# MAIN RENDER FUNCTION — REVENUE TAB
# ============================================================
def render_revenue(df):

    # --------------------------------------------------------
    # CALCULATE TOP-LINE REVENUE KPIs
    # --------------------------------------------------------
    total_gmv          = df["GMV"].sum()
    total_revenue      = df["Revenue"].sum()
    total_delivery_cost = df["Delivery Cost (how much we paid to the Rider)"].sum()
    total_profit       = df["Profit"].sum()
    profit_margin      = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    total_delivery_fee = df["Delivery Fee (Amount we Collected from the customer)"].sum()
    delivery_profit    = total_delivery_fee - total_delivery_cost

    # --------------------------------------------------------
    # LAYOUT — LEFT KPIs + RIGHT CHARTS
    # --------------------------------------------------------
    col_kpis, col_charts = st.columns([1, 2.5])

    with col_kpis:
        st.markdown(
            "<div class='section-title'>💰 Revenue Summary</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Key financial metrics for the selected period. "
            "GMV = total customer payments. "
            "Revenue = GMV minus product cost (COGS). "
            "Profit = Revenue minus delivery cost paid to riders. "
            "Delivery Profit = delivery fees collected minus delivery cost paid."
        )

        kpi_card("GMV", format_naira(total_gmv))
        kpi_card("Revenue", format_naira(total_revenue))
        kpi_card("Delivery Cost", format_naira(total_delivery_cost))
        kpi_card("Profit", format_naira(total_profit))

        margin_color = "kpi-positive" if profit_margin >= 0 else "kpi-negative"
        margin_str   = f"▲{profit_margin:.1f}%" if profit_margin >= 0 else f"▼{abs(profit_margin):.1f}%"
        kpi_card("Profit Margin", margin_str, color=margin_color)
        kpi_card("Delivery Profit", format_naira(delivery_profit))

    with col_charts:

        row1_left, row1_right = st.columns(2)

        # ---- CHART 1: Revenue by Day of Week ----
        with row1_left:
            st.markdown(
                "<div class='section-title'>📅 Revenue by Day</div>",
                unsafe_allow_html=True
            )
            chart_note(
                "Total revenue generated on each day of the week. "
                "Use this to identify peak days and plan rider "
                "availability and stock accordingly. "
                "The highest point is your busiest revenue day."
            )

            day_order = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
            day_map   = {
                "Sun": "Sunday", "Mon": "Monday", "Tue": "Tuesday",
                "Wed": "Wednesday", "Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday"
            }
            df["Full Day"] = df["Day of the Week"].map(day_map).fillna(df["Day of the Week"])

            revenue_by_day = df.groupby("Full Day")["Revenue"].sum().reset_index()
            revenue_by_day["Day Order"] = revenue_by_day["Full Day"].apply(
                lambda x: day_order.index(x) if x in day_order else 99
            )
            revenue_by_day = revenue_by_day.sort_values("Day Order")

            fig_day = go.Figure()
            fig_day.add_trace(go.Scatter(
                x=revenue_by_day["Full Day"],
                y=revenue_by_day["Revenue"],
                mode="markers+lines+text",
                marker=dict(color="#003399", size=12),
                line=dict(color="#003399", width=2),
                text=revenue_by_day["Revenue"].apply(format_naira),
                textposition="top center",
                textfont=dict(size=10, color="#333333")
            ))
            fig_day.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=5, r=5, t=10, b=5),
                xaxis=dict(showgrid=False, title=""),
                yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
                height=220
            )
            st.plotly_chart(fig_day, use_container_width=True)

        # ---- CHART 2: Revenue by Product Type ----
        with row1_right:
            st.markdown(
                "<div class='section-title'>🛢️ Revenue by Product</div>",
                unsafe_allow_html=True
            )
            chart_note(
                "Revenue split across product types. "
                "A dominant slice means heavy reliance on one product — "
                "a supply or pricing shock could significantly impact revenue. "
                "Healthy mix = more resilient business."
            )

            revenue_by_product = df.groupby("Order Type")["Revenue"].sum().reset_index()

            fig_product = px.pie(
                revenue_by_product,
                names="Order Type",
                values="Revenue",
                hole=0.55,
                color_discrete_sequence=["#003399", "#6699ff", "#ccd9ff"]
            )
            fig_product.update_traces(
                textinfo="label+percent",
                textfont_size=11
            )
            fig_product.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=5, r=5, t=10, b=5),
                showlegend=True,
                legend=dict(orientation="v", x=1, y=0.5),
                height=220
            )
            st.plotly_chart(fig_product, use_container_width=True)

        row2_left, row2_right = st.columns(2)

        # ---- CHART 3: Revenue by Area ----
        with row2_left:
            st.markdown(
                "<div class='section-title'>📍 Revenue by Area</div>",
                unsafe_allow_html=True
            )
            chart_note(
                "Total revenue per delivery area. "
                "Tallest bars are your highest-value markets — "
                "prioritise rider availability and pre-positioned stock there. "
                "Short bars may be underserved areas with growth potential."
            )

            revenue_by_area = df.groupby("Order Area/Location")[
                "Revenue"
            ].sum().reset_index().sort_values("Revenue", ascending=False)

            fig_area = px.bar(
                revenue_by_area,
                x="Order Area/Location",
                y="Revenue",
                text=revenue_by_area["Revenue"].apply(format_naira),
                color_discrete_sequence=["#003399"]
            )
            fig_area.update_traces(
                textposition="outside",
                textfont=dict(size=9, color="#333333")
            )
            fig_area.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=5, r=5, t=10, b=5),
                xaxis=dict(showgrid=False, title="", tickangle=-45, tickfont=dict(size=9)),
                yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
                height=250
            )
            st.plotly_chart(fig_area, use_container_width=True)

        # ---- CHART 4: Revenue by Station ----
        with row2_right:
            st.markdown(
                "<div class='section-title'>🏪 Revenue by Station</div>",
                unsafe_allow_html=True
            )
            chart_note(
                "Which fueling station contributes the most revenue. "
                "The longest bar is the station fulfilling the most "
                "high-value orders. Use this to assess station capacity "
                "and decide where to expand supply or add riders."
            )

            revenue_by_station = df.groupby("Station")[
                "Revenue"
            ].sum().reset_index().sort_values("Revenue", ascending=False)

            fig_station = px.bar(
                revenue_by_station,
                x="Revenue",
                y="Station",
                orientation="h",
                text=revenue_by_station["Revenue"].apply(format_naira),
                color_discrete_sequence=["#003399"]
            )
            fig_station.update_traces(
                textposition="outside",
                textfont=dict(size=10, color="#333333")
            )
            fig_station.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=5, r=5, t=10, b=5),
                xaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
                yaxis=dict(showgrid=False, title=""),
                height=250
            )
            st.plotly_chart(fig_station, use_container_width=True)

    # --------------------------------------------------------
    # PRODUCT REVENUE BY MONTH — Stacked Bar
    # --------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-title'>📅 Product Revenue by Month</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "Monthly revenue stacked by product type. "
        "Each colour represents one product — Petrol, Gas, or Engine Oil. "
        "Use this to spot seasonal product trends and shifts in customer mix. "
        "A growing green bar means gas demand is rising. "
        "A shrinking blue bar means petrol orders may be declining."
    )

    product_monthly = df.groupby(
        ["Year", "Month", "Month Name", "Order Type"]
    )["Revenue"].sum().reset_index()

    product_monthly["Month Label"] = product_monthly.apply(
        lambda r: pd.Timestamp(
            year=int(r["Year"]), month=int(r["Month"]), day=1
        ).strftime("%b %Y"), axis=1
    )
    product_monthly = product_monthly.sort_values(["Year", "Month"])

    product_types = product_monthly["Order Type"].unique()
    color_map = {
        "Petrol (Pms)": "#003399",
        "Gas (Lpg)":    "#6699ff",
        "Engine Oil":   "#ccd9ff",
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
            textfont=dict(color="white", size=10)
        ))

    fig_product_monthly.update_layout(
        barmode="stack",
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis=dict(showgrid=False, title="", tickfont=dict(color="#333333")),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0",
                   title="Revenue (₦)", tickfont=dict(color="#333333")),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=320
    )
    st.plotly_chart(fig_product_monthly, use_container_width=True)