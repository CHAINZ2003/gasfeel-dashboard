# ============================================================
# PRODUCT TAB — GasFeel Dashboard
# Shows Product Performance analysis.
# Charts: Volume by day, demand by area, revenue by product,
# avg orders per customer by week, reorder rate by month,
# and petrol customer weekly retention.
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
# MAIN RENDER FUNCTION — PRODUCT TAB
# ============================================================
def render_product(df):

    # --------------------------------------------------------
    # CALCULATE TOP-LINE PRODUCT KPIs
    # --------------------------------------------------------
    total_orders       = len(df)
    total_quantity     = df["Litre/Kg Sold"].sum()
    avg_order_value    = df["Revenue"].sum() / total_orders if total_orders > 0 else 0
    avg_litres_per_order = total_quantity / total_orders if total_orders > 0 else 0

    # Petrol frequency — avg orders per petrol customer per month
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

    # --------------------------------------------------------
    # TOP KPI ROW — 5 cards
    # --------------------------------------------------------
    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:
        kpi_card("Total Orders", f"{total_orders:,}")
    with k2:
        kpi_card("Total Quantity", f"{total_quantity:,.2f}")
    with k3:
        kpi_card("Avg Order Value", format_naira(avg_order_value))
    with k4:
        kpi_card("Avg Litres/Kg per Order", f"{avg_litres_per_order:.1f}")
    with k5:
        kpi_card("Avg Petrol Orders/Customer/Month", f"{avg_petrol_freq:.1f}x")

    st.markdown("""
        <p style='color:#888;font-size:12px;font-style:italic;margin:4px 0 16px 0;'>
            💡 Total Orders = all completed orders in selected period.
            Avg Order Value = Revenue ÷ Orders (what GasFeel earns per order after product cost).
            Avg Litres/Kg = how much product is delivered per order on average.
            Petrol Frequency = how many times per month the average petrol customer reorders.
        </p>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # ROW 2 — Volume by Day | Demand by Area
    # --------------------------------------------------------
    row1_left, row1_right = st.columns(2)

    # ---- CHART 1: Product Volume by Day ----
    with row1_left:
        st.markdown(
            "<div class='section-title'>📅 Product Volume by Day</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Total litres or kg sold on each day of the week. "
            "The highest point shows when customers order the most product. "
            "Use this to pre-position stock and ensure supply is ready "
            "on the heaviest demand days."
        )

        day_order = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
        day_map   = {
            "Sun": "Sunday", "Mon": "Monday", "Tue": "Tuesday",
            "Wed": "Wednesday", "Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday"
        }
        df["Full Day"] = df["Day of the Week"].map(day_map).fillna(df["Day of the Week"])

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
            textfont=dict(size=10, color="#333333")
        ))
        fig_vol.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=5, r=5, t=10, b=5),
            xaxis=dict(showgrid=False, title=""),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title="Litres / Kg"),
            height=230
        )
        st.plotly_chart(fig_vol, use_container_width=True)

    # ---- CHART 2: Product Demand by Area ----
    with row1_right:
        st.markdown(
            "<div class='section-title'>📍 Product Demand by Area</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Number of orders placed from each delivery area. "
            "Tallest bars are your busiest areas by order count — "
            "not necessarily highest revenue. "
            "High order count with low revenue means small orders. "
            "Use this alongside the Revenue by Area chart for full picture."
        )

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
        fig_demand.update_traces(
            textposition="outside",
            textfont=dict(size=9, color="#333333")
        )
        fig_demand.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=5, r=5, t=10, b=5),
            xaxis=dict(showgrid=False, title="", tickangle=-45, tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            height=230
        )
        st.plotly_chart(fig_demand, use_container_width=True)

    # --------------------------------------------------------
    # ROW 3 — Product Revenue | Avg Orders/Customer | Reorder Rate
    # --------------------------------------------------------
    row2_left, row2_mid, row2_right = st.columns(3)

    # ---- CHART 3: Revenue by Product Type ----
    with row2_left:
        st.markdown(
            "<div class='section-title'>🛢️ Revenue by Product Type</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Revenue share per product. "
            "Petrol dominating means GasFeel is heavily dependent "
            "on one product. Engine Oil and Gas diversification "
            "reduces revenue risk."
        )

        revenue_by_product = df.groupby("Order Type")["Revenue"].sum().reset_index()

        fig_donut = px.pie(
            revenue_by_product,
            names="Order Type",
            values="Revenue",
            hole=0.55,
            color_discrete_sequence=["#003399", "#6699ff", "#ccd9ff"]
        )
        fig_donut.update_traces(textinfo="label+percent", textfont_size=10)
        fig_donut.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=5, r=5, t=10, b=5),
            showlegend=False,
            height=250
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    # ---- CHART 4: Avg Orders per Customer by Week ----
    with row2_mid:
        st.markdown(
            "<div class='section-title'>👤 Avg Orders/Customer by Week</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Average number of orders placed per customer each week. "
            "Rising trend = customers are ordering more frequently. "
            "Falling trend = engagement is dropping — investigate. "
            "Target: push this above 2.0 orders per customer per week."
        )

        orders_per_week = df.groupby(
            ["Week", "Customer Name"]
        )["Order ID"].count().reset_index()
        avg_orders_per_week = orders_per_week.groupby(
            "Week"
        )["Order ID"].mean().reset_index()
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
            textfont=dict(size=11, color="#333333")
        ))
        for _, row in avg_orders_per_week.iterrows():
            fig_avg.add_shape(
                type="line",
                x0=row["Week Label"], x1=row["Week Label"],
                y0=0, y1=row["Avg Orders"],
                line=dict(color="#003399", width=2)
            )
        fig_avg.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=5, r=5, t=10, b=5),
            xaxis=dict(showgrid=False, title=""),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            height=250
        )
        st.plotly_chart(fig_avg, use_container_width=True)

    # ---- CHART 5: Reorder Rate % by Month ----
    with row2_right:
        st.markdown(
            "<div class='section-title'>🔄 Reorder Rate % by Month</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Percentage of customers who placed more than one order "
            "within each month. "
            "High reorder rate = loyal, engaged customers. "
            "Low rate = mostly one-time buyers — focus on "
            "re-engagement campaigns to bring them back."
        )

        monthly_reorder = []
        for (year, month), month_df in df.groupby(["Year", "Month"]):
            customer_counts = month_df.groupby("Customer Name")["Order ID"].count()
            repeat = (customer_counts > 1).sum()
            total  = customer_counts.count()
            rate   = (repeat / total * 100) if total > 0 else 0
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
        fig_reorder.update_traces(
            textposition="outside",
            textfont=dict(size=10, color="#333333")
        )
        fig_reorder.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=5, r=5, t=10, b=5),
            xaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            yaxis=dict(showgrid=False, title="", autorange="reversed"),
            height=250
        )
        st.plotly_chart(fig_reorder, use_container_width=True)

    # ============================================================
    # PETROL CUSTOMER RETENTION — Weekly Rolling Analysis
    # Independent of sidebar filters. Has its own controls.
    # ============================================================
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-title'>🔄 Petrol Customer Weekly Retention</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "Shows what % of petrol customers who ordered in a given week "
        "came back the following week. "
        "Green bars = strong retention (60%+). "
        "Amber bars = moderate (40-60%). "
        "Red bars = poor retention — these customers are going elsewhere. "
        "This section uses ALL data regardless of sidebar filters."
    )

    # Load full unfiltered data for this section
    from data_loader import load_orders as _load_orders
    full_df = _load_orders()

    petrol_only = full_df[
        full_df["Order Type"].str.contains("Petrol|PMS", case=False, na=False)
    ].copy()

    # Independent controls
    ctrl_col1, ctrl_col2 = st.columns([1, 2])

    with ctrl_col1:
        week_window = st.radio(
            "Window Size",
            options=[5, 7],
            index=0,
            horizontal=True,
            key="petrol_retention_window"
        )

    petrol_only["Week Start"] = petrol_only["Date of Order"].dt.to_period("W").apply(
        lambda r: r.start_time
    )
    available_weeks = sorted(petrol_only["Week Start"].dropna().unique())

    with ctrl_col2:
        if len(available_weeks) > week_window:
            default_end = len(available_weeks) - 1
            selected_end_idx = st.slider(
                "Ending Week",
                min_value=week_window - 1,
                max_value=len(available_weeks) - 1,
                value=default_end,
                key="petrol_retention_end",
                format=""
            )
            selected_weeks = available_weeks[
                selected_end_idx - week_window + 1: selected_end_idx + 1
            ]
        else:
            selected_weeks = available_weeks

    if len(selected_weeks) < 2:
        st.info("Not enough weekly data to calculate retention yet.")
        return

    # Calculate weekly retention
    weekly_customers = {}
    for week in selected_weeks:
        week_end  = week + pd.Timedelta(days=6)
        customers = set(
            petrol_only[
                (petrol_only["Date of Order"].dt.normalize() >= pd.Timestamp(week)) &
                (petrol_only["Date of Order"].dt.normalize() <= week_end)
            ]["Customer Name"].dropna().unique()
        )
        weekly_customers[week] = customers

    retention_rows = []
    for i in range(1, len(selected_weeks)):
        current_week  = selected_weeks[i]
        previous_week = selected_weeks[i - 1]

        prev_customers    = weekly_customers[previous_week]
        current_customers = weekly_customers[current_week]

        if len(prev_customers) == 0:
            continue

        retained    = len(prev_customers & current_customers)
        new_this_wk = len(current_customers - prev_customers)
        lost        = len(prev_customers - current_customers)
        retention   = (retained / len(prev_customers)) * 100
        wk_label    = f"WK {current_week.strftime('%d %b')}"

        retention_rows.append({
            "Week":           wk_label,
            "Week Date":      current_week,
            "Prev Customers": len(prev_customers),
            "Retained":       retained,
            "New":            new_this_wk,
            "Lost":           lost,
            "Retention %":    round(retention, 1)
        })

    if not retention_rows:
        st.info("Not enough data to calculate retention.")
        return

    retention_df = pd.DataFrame(retention_rows)

    avg_retention  = retention_df["Retention %"].mean()
    best_week      = retention_df.loc[retention_df["Retention %"].idxmax(), "Week"]
    best_rate      = retention_df["Retention %"].max()
    worst_week     = retention_df.loc[retention_df["Retention %"].idxmin(), "Week"]
    worst_rate     = retention_df["Retention %"].min()
    total_lost     = retention_df["Lost"].sum()

    m1, m2, m3, m4 = st.columns(4)

    def mini_card(col, label, value, color="#003399"):
        with col:
            st.markdown(f"""
                <div style="background:white;border-radius:12px;padding:14px 16px;
                            box-shadow:0 4px 12px rgba(0,51,153,0.10);
                            border-left:5px solid {color};margin-bottom:14px;">
                    <div style="color:#999;font-size:10px;font-weight:700;
                                text-transform:uppercase;letter-spacing:1px;
                                margin-bottom:6px;">{label}</div>
                    <div style="color:#001f6e;font-size:22px;font-weight:800;">{value}</div>
                </div>
            """, unsafe_allow_html=True)

    mini_card(m1, f"Avg Retention ({week_window}wk)",
              f"{avg_retention:.1f}%",
              "#00aa44" if avg_retention >= 50 else "#f0a500")
    mini_card(m2, "Best Week",   f"{best_week} ({best_rate:.0f}%)", "#00aa44")
    mini_card(m3, "Worst Week",  f"{worst_week} ({worst_rate:.0f}%)", "#cc0000")
    mini_card(m4, "Avg Lost/Week",
              f"{total_lost // max(len(retention_df), 1)}", "#cc0000")

    st.markdown("<br>", unsafe_allow_html=True)

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown(
            "<div class='section-title'>📈 Retention Rate by Week</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Each bar shows what % of last week's petrol customers "
            "came back this week. "
            "Green = 60%+ retention. Amber = 40-60%. Red = below 40%. "
            "The dashed line is the average across the selected window."
        )

        bar_colors = [
            "#00aa44" if r >= 60 else ("#f0a500" if r >= 40 else "#cc0000")
            for r in retention_df["Retention %"]
        ]

        fig_ret = go.Figure()
        fig_ret.add_trace(go.Bar(
            x=retention_df["Week"],
            y=retention_df["Retention %"],
            marker_color=bar_colors,
            text=retention_df["Retention %"].apply(lambda x: f"{x:.1f}%"),
            textposition="outside",
            textfont=dict(size=11, color="#333333")
        ))
        fig_ret.add_hline(
            y=avg_retention,
            line_dash="dash",
            line_color="#003399",
            annotation_text=f"Avg {avg_retention:.1f}%",
            annotation_position="top right"
        )
        fig_ret.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=5, r=5, t=20, b=5),
            xaxis=dict(showgrid=False, title=""),
            yaxis=dict(
                showgrid=True, gridcolor="#f0f0f0",
                title="Retention %", range=[0, 110]
            ),
            height=300
        )
        st.plotly_chart(fig_ret, use_container_width=True)

    with chart_col2:
        st.markdown(
            "<div class='section-title'>👥 Retained vs Lost vs New</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Each week broken into three groups: "
            "Blue = customers who came back from last week. "
            "Green = brand new customers this week. "
            "Red = customers from last week who did not return. "
            "Ideal = tall blue, growing green, shrinking red."
        )

        fig_stack = go.Figure()
        fig_stack.add_trace(go.Bar(
            name="Retained",
            x=retention_df["Week"],
            y=retention_df["Retained"],
            marker_color="#003399",
            text=retention_df["Retained"],
            textposition="inside",
            textfont=dict(color="white", size=10)
        ))
        fig_stack.add_trace(go.Bar(
            name="New",
            x=retention_df["Week"],
            y=retention_df["New"],
            marker_color="#00aa44",
            text=retention_df["New"],
            textposition="inside",
            textfont=dict(color="white", size=10)
        ))
        fig_stack.add_trace(go.Bar(
            name="Lost",
            x=retention_df["Week"],
            y=retention_df["Lost"],
            marker_color="#cc0000",
            text=retention_df["Lost"],
            textposition="inside",
            textfont=dict(color="white", size=10)
        ))
        fig_stack.update_layout(
            barmode="group",
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=5, r=5, t=20, b=5),
            xaxis=dict(showgrid=False, title=""),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title="Customers"),
            legend=dict(
                orientation="h",
                yanchor="bottom", y=1.02,
                xanchor="right", x=1
            ),
            height=300
        )
        st.plotly_chart(fig_stack, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-title'>📋 Weekly Retention Detail</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "Full breakdown per week. "
        "Previous Week Customers = how many unique petrol customers ordered last week. "
        "Came Back = how many of those returned this week. "
        "Did Not Return = lost customers that week. "
        "New This Week = first-time or returning after long gap."
    )

    display_df = retention_df[[
        "Week", "Prev Customers", "Retained",
        "Lost", "New", "Retention %"
    ]].copy()
    display_df["Retention %"] = display_df["Retention %"].astype(str) + "%"
    display_df = display_df.rename(columns={
        "Week":           "Week",
        "Prev Customers": "Previous Week Customers",
        "Retained":       "Came Back",
        "Lost":           "Did Not Return",
        "New":            "New This Week",
        "Retention %":    "Retention Rate"
    })
    st.dataframe(display_df, use_container_width=True, hide_index=True)