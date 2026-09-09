# ============================================================
# OPERATION TAB — GasFeel Dashboard
# Shows operational performance metrics.
# Charts: Delivery time by area, rider performance,
# orders per rider, hourly pattern, free vs paid delivery.
# All charts include descriptions for team readability.
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
# MAIN RENDER FUNCTION — OPERATION TAB
# ============================================================
def render_operation(df):

    # --------------------------------------------------------
    # CALCULATE TOP-LINE OPERATION KPIs
    # --------------------------------------------------------
    total_riders    = df["Rider Name"].nunique()
    total_locations = df["Order Area/Location"].nunique()
    total_stations  = df["Station"].nunique()
    total_orders    = len(df)

    # Average time metrics
    avg_total_time      = df["Total Duration (mins)"].mean()
    avg_initiation_time = df["Initiation Duration (mins)"].mean()
    avg_delivery_time   = df["Delivery Duration (mins)"].mean()

    avg_total_time      = avg_total_time if pd.notna(avg_total_time) else 0
    avg_initiation_time = avg_initiation_time if pd.notna(avg_initiation_time) else 0
    avg_delivery_time   = avg_delivery_time if pd.notna(avg_delivery_time) else 0

    # On-time rate — based on total journey <= 10 mins
    on_time_count = df["On Time"].sum()
    on_time_rate  = (on_time_count / total_orders * 100) if total_orders > 0 else 0

    # --------------------------------------------------------
    # TOP KPI ROW
    # --------------------------------------------------------
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        kpi_card("Total Riders", str(total_riders))
    with k2:
        st.markdown(f"""
            <div class='kpi-card'>
                <div class='kpi-label'>Locations</div>
                <div class='kpi-value'>{total_locations}</div>
                <div class='kpi-label' style='margin-top:6px;'>
                    Stations: <b>{total_stations}</b>
                </div>
            </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
            <div class='kpi-card'>
                <div class='kpi-label'>Avg Total Time</div>
                <div class='kpi-value'>{avg_total_time:.1f} mins</div>
                <div class='kpi-label' style='margin-top:6px;'>
                    Initiation: <b>{avg_initiation_time:.1f} mins</b>
                    &nbsp;|&nbsp;
                    Delivery: <b>{avg_delivery_time:.1f} mins</b>
                </div>
            </div>
        """, unsafe_allow_html=True)
    with k4:
        on_time_color = "kpi-positive" if on_time_rate >= 70 else "kpi-negative"
        on_time_str   = f"▲{on_time_rate:.1f}%"
        kpi_card("On-Time Rate (≤10 mins)", on_time_str, color=on_time_color)

    st.markdown("""
        <p style='color:#888;font-size:12px;font-style:italic;margin:4px 0 16px 0;'>
            💡 Total Time = order placed to completion (customer experience).
            Initiation = order placed to rider starting (response speed).
            Delivery = rider started to order completed (delivery speed).
            On-Time Rate = % of orders completed within 10 minutes total.
        </p>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # ROW 2 — Delivery Time by Area | Rider Performance
    # --------------------------------------------------------
    row1_left, row1_right = st.columns(2)

    # ---- CHART 1: Delivery Time by Area ----
    with row1_left:
        st.markdown(
            "<div class='section-title'>📍 Delivery Time by Area (mins)</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Average total delivery time per area. "
            "Tallest bars = slowest areas — investigate why. "
            "Could be distance from station, traffic, or "
            "rider availability. Use this to decide where to "
            "add stations or reposition riders."
        )

        time_by_area = df.groupby("Order Area/Location")[
            "Total Duration (mins)"
        ].mean().reset_index()
        time_by_area.columns = ["Area", "Avg Time"]
        time_by_area = time_by_area.dropna()
        time_by_area = time_by_area.sort_values("Avg Time", ascending=False)
        time_by_area["Avg Time"] = time_by_area["Avg Time"].round(1)

        fig_area = px.bar(
            time_by_area,
            x="Area",
            y="Avg Time",
            text="Avg Time",
            color_discrete_sequence=["#003399"]
        )
        fig_area.update_traces(
            textposition="outside",
            textfont=dict(size=9, color="#333333")
        )
        fig_area.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=5, r=5, t=10, b=5),
            xaxis=dict(
                showgrid=False, title="",
                tickangle=-45, tickfont=dict(size=9)
            ),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title="Mins"),
            height=280
        )
        st.plotly_chart(fig_area, use_container_width=True)

    # ---- CHART 2: Rider Avg Delivery Time ----
    with row1_right:
        st.markdown(
            "<div class='section-title'>🚴 Rider Avg Delivery Time (mins)</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Average delivery time per rider. "
            "Green dots = within 10-minute target. "
            "Red dots = above target — needs coaching or review. "
            "The dashed yellow line marks the 10-minute threshold. "
            "Consistently red riders may need route or workload adjustment."
        )

        rider_time = df.groupby("Rider Name")[
            "Delivery Duration (mins)"
        ].mean().reset_index()
        rider_time.columns = ["Rider", "Avg Time"]
        rider_time = rider_time.dropna()
        rider_time["Avg Time"] = rider_time["Avg Time"].round(1)
        rider_time = rider_time.sort_values("Avg Time")
        rider_time["Color"] = rider_time["Avg Time"].apply(
            lambda x: "#00aa44" if x <= 10 else "#cc0000"
        )

        fig_rider = go.Figure()
        fig_rider.add_trace(go.Scatter(
            x=rider_time["Rider"],
            y=rider_time["Avg Time"],
            mode="markers+text",
            marker=dict(color=rider_time["Color"], size=14),
            text=rider_time["Avg Time"],
            textposition="top center",
            textfont=dict(size=10, color="#333333")
        ))
        for _, row in rider_time.iterrows():
            fig_rider.add_shape(
                type="line",
                x0=row["Rider"], x1=row["Rider"],
                y0=0, y1=row["Avg Time"],
                line=dict(color=row["Color"], width=2)
            )
        fig_rider.add_hline(
            y=10,
            line_dash="dash",
            line_color="#f0a500",
            annotation_text="10 min threshold",
            annotation_position="top right"
        )
        fig_rider.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=5, r=5, t=10, b=5),
            xaxis=dict(showgrid=False, title=""),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title="Mins"),
            height=280
        )
        st.plotly_chart(fig_rider, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # ROW 3 — Orders per Rider | Hourly Pattern | Free vs Paid
    # --------------------------------------------------------
    row2_left, row2_mid, row2_right = st.columns(3)

    # ---- CHART 3: Orders per Rider ----
    with row2_left:
        st.markdown(
            "<div class='section-title'>📦 Orders per Rider</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Total orders handled by each rider. "
            "The longest bar is your most active rider. "
            "Very short bars may indicate availability issues "
            "or underutilised riders. "
            "Uneven distribution may cause burnout for top riders."
        )

        orders_per_rider = df.groupby("Rider Name")[
            "Order ID"
        ].count().reset_index()
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
        fig_orders.update_traces(
            textposition="outside",
            textfont=dict(size=10, color="#333333")
        )
        fig_orders.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=5, r=5, t=10, b=5),
            xaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            yaxis=dict(showgrid=False, title=""),
            height=280
        )
        st.plotly_chart(fig_orders, use_container_width=True)

    # ---- CHART 4: Hourly Order Pattern ----
    with row2_mid:
        st.markdown(
            "<div class='section-title'>🕐 Hourly Order Pattern</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "When customers place orders throughout the day. "
            "Evening is typically peak for fuel businesses. "
            "Use this to schedule rider shifts around peak hours "
            "and avoid understaffing during busy periods."
        )

        df["Order Hour"] = pd.to_datetime(
            df["Order Time"].astype(str).str.strip(),
            format="%I:%M:%S %p", errors="coerce"
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
            lambda x: time_slot(x) if pd.notna(x) else "Unknown"
        )

        slot_order = ["Morning", "Afternoon", "Evening", "Night"]
        hourly = df[df["Time Slot"] != "Unknown"][
            "Time Slot"
        ].value_counts().reindex(slot_order).fillna(0).reset_index()
        hourly.columns = ["Time Slot", "Orders"]

        fig_hourly = px.bar(
            hourly,
            x="Orders",
            y="Time Slot",
            orientation="h",
            text="Orders",
            color_discrete_sequence=["#003399"]
        )
        fig_hourly.update_traces(
            textposition="outside",
            textfont=dict(size=10, color="#333333")
        )
        fig_hourly.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=5, r=5, t=10, b=5),
            xaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            yaxis=dict(
                showgrid=False, title="",
                categoryorder="array",
                categoryarray=slot_order[::-1]
            ),
            height=280
        )
        st.plotly_chart(fig_hourly, use_container_width=True)

    # ---- CHART 5: Free vs Paid Delivery ----
    with row2_right:
        st.markdown(
            "<div class='section-title'>🆓 Free vs Paid Delivery</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Split between orders with free delivery and paid delivery. "
            "A large free slice means GasFeel is subsidising delivery costs. "
            "If more than 50% are free, review the free delivery "
            "eligibility policy — it may be reducing profitability."
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
            margin=dict(l=5, r=5, t=10, b=5),
            showlegend=True,
            legend=dict(orientation="v", x=1, y=0.5),
            height=280
        )
        st.plotly_chart(fig_delivery, use_container_width=True)