# ============================================================
# OPERATION TAB — GasFeel Dashboard
# Shows Operation Dashboard matching the Excel tab.
# KPIs: Total Riders, Avg Delivery Time, Locations, On-Time Rate
# Charts: Delivery time by area, rider performance, orders per
#         rider, hourly pattern, free vs paid delivery
# Called from app.py with filtered_df as input.
# ============================================================

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


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
# MAIN RENDER FUNCTION — OPERATION TAB
# ============================================================

def render_operation(df):

    # --------------------------------------------------------
    # CALCULATE TOP-LINE OPERATION KPIs
    # --------------------------------------------------------

    # Total unique riders in the filtered dataset
    total_riders = df["Rider Name"].nunique()

    # Average delivery duration in minutes (25 min = on-time threshold)
    avg_delivery_time = df["Delivery Duration (mins)"].mean()
    avg_delivery_time = avg_delivery_time if not pd.isna(avg_delivery_time) else 0

    # Total unique delivery locations
    total_locations = df["Order Area/Location"].nunique()

    # Total unique stations
    total_stations = df["Station"].nunique()

    # On-time rate = orders delivered within 25 mins / total orders
    on_time_count = df["On Time"].sum()
    total_orders = len(df)
    on_time_rate = (on_time_count / total_orders * 100) if total_orders > 0 else 0

    # --------------------------------------------------------
    # TOP KPI ROW — 4 cards across
    # --------------------------------------------------------
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        kpi_card("Total Riders", str(total_riders))

    with k2:
        kpi_card("Avg Delivery Time", f"{avg_delivery_time:.1f} mins")

    with k3:
        # Show locations and stations together in one card
        st.markdown(f"""
            <div class='kpi-card'>
                <div class='kpi-label'>Locations</div>
                <div class='kpi-value'>{total_locations}</div>
                <div class='kpi-label' style='margin-top:6px;'>Stations: <b>{total_stations}</b></div>
            </div>
        """, unsafe_allow_html=True)

    with k4:
        on_time_color = "kpi-positive" if on_time_rate >= 70 else "kpi-negative"
        on_time_str = f"▲{on_time_rate:.1f}%"
        st.metric(
            label="On-Time Rate",
            value="",
            delta=f"{on_time_rate:.1f}%",
            delta_color="normal"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # ROW 2 — DELIVERY TIME BY AREA | RIDER PERFORMANCE
    # --------------------------------------------------------
    row1_left, row1_right = st.columns(2)

    # ---- CHART 1: Longest and Shortest Delivery Time by Area ----
    with row1_left:
        st.markdown(
            "<div class='section-title'>📍 Delivery Time by Area (mins)</div>",
            unsafe_allow_html=True
        )

        # Average delivery duration grouped by area
        time_by_area = df.groupby("Order Area/Location")[
            "Delivery Duration (mins)"
        ].mean().reset_index()
        time_by_area.columns = ["Area", "Avg Delivery Time"]
        time_by_area = time_by_area.dropna()
        time_by_area = time_by_area.sort_values("Avg Delivery Time", ascending=False)
        time_by_area["Avg Delivery Time"] = time_by_area["Avg Delivery Time"].round(1)

        fig_area = px.bar(
            time_by_area,
            x="Area",
            y="Avg Delivery Time",
            text="Avg Delivery Time",
            color_discrete_sequence=["#003399"]
        )
        fig_area.update_traces(textposition="outside", textfont_size=9)
        fig_area.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=10, r=30, t=20, b=10),
            xaxis=dict(showgrid=False, title="", tickangle=-45, tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title="Mins"),
            height=260
        )
        st.plotly_chart(fig_area, use_container_width=True)

    # ---- CHART 2: Rider Performance — Fastest vs Needs Improvement ----
    with row1_right:
        st.markdown(
            "<div class='section-title'>🚴 Rider Avg Delivery Time (mins)</div>",
            unsafe_allow_html=True
        )

        # Average delivery time per rider — lower is better
        rider_time = df.groupby("Rider Name")[
            "Delivery Duration (mins)"
        ].mean().reset_index()
        rider_time.columns = ["Rider", "Avg Time"]
        rider_time = rider_time.dropna()
        rider_time["Avg Time"] = rider_time["Avg Time"].round(1)
        rider_time = rider_time.sort_values("Avg Time")

        # Colour riders — green if at or below 25 mins, red if above
        rider_time["Color"] = rider_time["Avg Time"].apply(
            lambda x: "#00aa44" if x <= 25 else "#cc0000"
        )

        fig_rider = go.Figure()
        fig_rider.add_trace(go.Scatter(
            x=rider_time["Rider"],
            y=rider_time["Avg Time"],
            mode="markers+text",
            marker=dict(color=rider_time["Color"], size=14),
            text=rider_time["Avg Time"],
            textposition="top center",
            textfont=dict(size=10)
        ))
        # Lollipop lines from zero to each marker
        for _, row in rider_time.iterrows():
            fig_rider.add_shape(
                type="line",
                x0=row["Rider"], x1=row["Rider"],
                y0=0, y1=row["Avg Time"],
                line=dict(color=row["Color"], width=2)
            )
        # 25-minute on-time threshold reference line
        fig_rider.add_hline(
            y=25,
            line_dash="dash",
            line_color="#f0a500",
            annotation_text="25 min threshold",
            annotation_position="top right"
        )
        fig_rider.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=10, r=30, t=20, b=10),
            xaxis=dict(showgrid=False, title=""),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title="Mins"),
            height=260
        )
        st.plotly_chart(fig_rider, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # ROW 3 — ORDERS PER RIDER | HOURLY PATTERN | FREE VS PAID
    # --------------------------------------------------------
    row2_left, row2_mid, row2_right = st.columns(3)

    # ---- CHART 3: Which Rider Handles Most and Least Orders ----
    with row2_left:
        st.markdown(
            "<div class='section-title'>📦 Orders per Rider</div>",
            unsafe_allow_html=True
        )

        orders_per_rider = df.groupby("Rider Name")["Order ID"].count().reset_index()
        orders_per_rider.columns = ["Rider", "Orders"]
        orders_per_rider = orders_per_rider.sort_values("Orders", ascending=True)

        fig_orders = px.bar(
            orders_per_rider,
            x="Orders",
            y="Rider",
            orientation="h",
            text="Orders",
            color_discrete_sequence=["#003399"]
        )
        fig_orders.update_traces(textposition="outside", textfont_size=10)
        fig_orders.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=10, r=30, t=20, b=10),
            xaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            yaxis=dict(showgrid=False, title=""),
            height=260
        )
        st.plotly_chart(fig_orders, use_container_width=True)

    # ---- CHART 4: Hourly Order Pattern ----
    with row2_mid:
        st.markdown(
            "<div class='section-title'>🕐 Hourly Order Pattern</div>",
            unsafe_allow_html=True
        )

        # Extract hour from Order Time and group into time slots
        df["Order Hour"] = pd.to_datetime(
            df["Order Time"], format="%I:%M:%S %p", errors="coerce"
        ).dt.hour

        def time_slot(hour):
            if 5 <= hour < 12:
                return "Morning"
            elif 12 <= hour < 17:
                return "Afternoon"
            elif 17 <= hour < 21:
                return "Evening"
            else:
                return "Night"

        df["Time Slot"] = df["Order Hour"].apply(
            lambda x: time_slot(x) if not pd.isna(x) else "Unknown"
        )

        slot_order = ["Morning", "Afternoon", "Evening", "Night"]
        hourly = df[df["Time Slot"] != "Unknown"]["Time Slot"].value_counts()
        hourly = hourly.reindex(slot_order).fillna(0).reset_index()
        hourly.columns = ["Time Slot", "Orders"]

        fig_hourly = px.bar(
            hourly,
            x="Orders",
            y="Time Slot",
            orientation="h",
            text="Orders",
            color_discrete_sequence=["#003399"]
        )
        fig_hourly.update_traces(textposition="outside", textfont_size=10)
        fig_hourly.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=10, r=30, t=20, b=10),
            xaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            yaxis=dict(showgrid=False, title="", categoryorder="array",
                      categoryarray=slot_order[::-1]),
            height=260
        )
        st.plotly_chart(fig_hourly, use_container_width=True)

    # ---- CHART 5: Free vs Paid Delivery ----
    with row2_right:
        st.markdown(
            "<div class='section-title'>🆓 Free vs Paid Delivery</div>",
            unsafe_allow_html=True
        )

        delivery_type = df["Delivery Type"].value_counts().reset_index()
        delivery_type.columns = ["Type", "Count"]

        fig_delivery = px.pie(
            delivery_type,
            names="Type",
            values="Count",
            hole=0.55,
            color="Type",
            color_discrete_map={"Free": "#003399", "Paid": "#ccd9ff"}
        )
        fig_delivery.update_traces(
            textinfo="label+value",
            textfont_size=11
        )
        fig_delivery.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=10, r=30, t=20, b=10),
            showlegend=True,
            legend=dict(orientation="v", x=1, y=0.5),
            height=260
        )
        st.plotly_chart(fig_delivery, use_container_width=True)