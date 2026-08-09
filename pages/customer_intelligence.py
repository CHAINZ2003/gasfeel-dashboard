# ============================================================
# CUSTOMER INTELLIGENCE TAB — GasFeel Dashboard
# Deep customer analysis using enriched Supabase customers table.
# Shows membership, deposits, run-out dates, acquisition channels,
# retention cohorts, and product frequency analysis.
# ============================================================

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
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
# HELPER — LOAD CUSTOMER DATA FROM SUPABASE
# ============================================================
@st.cache_data(ttl=600)
def load_customer_intelligence():
    try:
        supabase = create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_KEY"]
        )

        # Fetch all customers
        all_customers = []
        offset = 0
        while True:
            result = supabase.table("customers").select(
                "whatsapp_number,name,customer_type,is_member,"
                "membership_deliveries_used,membership_deliveries_total,"
                "deposit_balance,last_bought_date,run_out_date,"
                "next_reachout_date,acquisition_channel,usual_kg,"
                "daily_fuel_amount,owning_agent_id,is_active,"
                "created_at,primary_area_id"
            ).range(offset, offset + 999).execute()
            if not result.data:
                break
            all_customers.extend(result.data)
            if len(result.data) < 1000:
                break
            offset += 1000

        df = pd.DataFrame(all_customers)

        # Convert date columns
        date_cols = [
            "last_bought_date", "run_out_date",
            "next_reachout_date", "created_at"
        ]
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        # Convert numeric columns
        num_cols = [
            "deposit_balance", "usual_kg",
            "daily_fuel_amount", "membership_deliveries_used",
            "membership_deliveries_total"
        ]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        return df

    except Exception as e:
        st.error(f"Failed to load customer intelligence: {e}")
        return pd.DataFrame()


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================
def render_customer_intelligence(orders_df):

    today = pd.Timestamp.now().normalize()

    # Load enriched customer data from Supabase
    customers_df = load_customer_intelligence()

    if customers_df.empty:
        st.info("No customer intelligence data available.")
        return

    # --------------------------------------------------------
    # SECTION 1 — TOP KPI SNAPSHOT
    # --------------------------------------------------------
    st.markdown(
        "<div class='section-title'>⚡ Customer Intelligence Snapshot</div>",
        unsafe_allow_html=True
    )

    total_customers    = len(customers_df)
    active_customers   = customers_df["is_active"].sum()
    member_customers   = customers_df["is_member"].sum()
    total_deposit      = customers_df["deposit_balance"].sum()
    avg_deposit        = customers_df[
        customers_df["deposit_balance"] > 0
    ]["deposit_balance"].mean()

    # Customers running out in next 7 days
    running_out_soon = customers_df[
        (customers_df["run_out_date"] >= today) &
        (customers_df["run_out_date"] <= today + timedelta(days=7))
    ]

    # Customers due for reachout today or overdue
    reachout_due = customers_df[
        customers_df["next_reachout_date"].notna() &
        (customers_df["next_reachout_date"] <= today)
    ]

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

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1:
        snap("Total Customers", f"{total_customers:,}", "in database", "#003399")
    with k2:
        snap("Active Members", f"{int(member_customers):,}",
             f"{(member_customers/total_customers*100):.1f}% of base", "#003399")
    with k3:
        snap("Deposit Balance", format_naira(total_deposit),
             f"avg {format_naira(avg_deposit)}/customer", "#003399")
    with k4:
        snap("Running Out Soon", f"{len(running_out_soon):,}",
             "within 7 days", "#cc0000" if len(running_out_soon) > 10 else "#f0a500")
    with k5:
        snap("Reachout Due", f"{len(reachout_due):,}",
             "today or overdue", "#f0a500")
    with k6:
        mem_util = (
            customers_df["membership_deliveries_used"].sum() /
            customers_df["membership_deliveries_total"].sum() * 100
            if customers_df["membership_deliveries_total"].sum() > 0 else 0
        )
        snap("Membership Utilization", f"{mem_util:.1f}%",
             "deliveries used", "#003399")

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # SECTION 2 — RUNNING OUT SOON LIST
    # Most actionable insight — who to call TODAY
    # --------------------------------------------------------
    st.markdown(
        "<div class='section-title'>🔴 Customers Running Out This Week — Call Now</div>",
        unsafe_allow_html=True
    )

    if not running_out_soon.empty:
        runout_display = running_out_soon[[
            "name", "whatsapp_number", "customer_type",
            "usual_kg", "run_out_date", "last_bought_date"
        ]].copy()
        runout_display["Days Until Empty"] = (
            runout_display["run_out_date"] - today
        ).dt.days
        runout_display = runout_display.sort_values("Days Until Empty")
        runout_display["run_out_date"] = runout_display["run_out_date"].dt.strftime("%d %b %Y")
        runout_display["last_bought_date"] = runout_display["last_bought_date"].dt.strftime("%d %b %Y")
        runout_display = runout_display.rename(columns={
            "name": "Customer",
            "whatsapp_number": "WhatsApp",
            "customer_type": "Type",
            "usual_kg": "Usual Qty",
            "run_out_date": "Runs Out",
            "last_bought_date": "Last Order"
        })
        st.dataframe(runout_display, use_container_width=True, hide_index=True)
    else:
        st.success("No customers running out in the next 7 days.")

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # SECTION 3 — REACHOUT SCHEDULE
    # --------------------------------------------------------
    st.markdown(
        "<div class='section-title'>📞 Reachout Due Today or Overdue</div>",
        unsafe_allow_html=True
    )

    if not reachout_due.empty:
        reachout_display = reachout_due[[
            "name", "whatsapp_number", "customer_type",
            "next_reachout_date", "last_bought_date", "owning_agent_id"
        ]].copy()
        reachout_display["Days Overdue"] = (
            today - reachout_display["next_reachout_date"]
        ).dt.days
        reachout_display = reachout_display.sort_values("Days Overdue", ascending=False)
        reachout_display["next_reachout_date"] = reachout_display["next_reachout_date"].dt.strftime("%d %b %Y")
        reachout_display["last_bought_date"] = pd.to_datetime(
            reachout_display["last_bought_date"], errors="coerce"
        ).dt.strftime("%d %b %Y")
        reachout_display = reachout_display.rename(columns={
            "name": "Customer",
            "whatsapp_number": "WhatsApp",
            "customer_type": "Type",
            "next_reachout_date": "Due Date",
            "last_bought_date": "Last Order",
            "owning_agent_id": "Agent"
        })
        st.dataframe(reachout_display, use_container_width=True, hide_index=True)
    else:
        st.success("No reachouts overdue today.")

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # SECTION 4 — MEMBER VS NON-MEMBER ANALYSIS
    # --------------------------------------------------------
    st.markdown(
        "<div class='section-title'>👑 Member vs Non-Member Analysis</div>",
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:
        # Member vs Non-member customer count
        member_counts = pd.DataFrame({
            "Status": ["Member", "Non-Member"],
            "Count": [
                int(member_customers),
                int(total_customers - member_customers)
            ]
        })

        fig_mem = px.pie(
            member_counts,
            names="Status", values="Count",
            hole=0.55,
            color_discrete_sequence=["#003399", "#ccd9ff"]
        )
        fig_mem.update_traces(textinfo="label+value+percent", textfont_size=11)
        fig_mem.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=5, r=5, t=20, b=5),
            height=280
        )
        st.markdown(
            "<div class='section-title'>Customer Count</div>",
            unsafe_allow_html=True
        )
        st.plotly_chart(fig_mem, use_container_width=True)

    with col2:
        # Member vs Non-member revenue from orders
        if "Customer Phone" in orders_df.columns:
            member_phones = set(
                customers_df[customers_df["is_member"] == True][
                    "whatsapp_number"
                ].astype(str).tolist()
            )
            orders_df["Is Member"] = orders_df["Customer Phone"].astype(str).isin(member_phones)
            mem_rev = orders_df.groupby("Is Member")["Revenue"].sum().reset_index()
            mem_rev["Status"] = mem_rev["Is Member"].map({True: "Member", False: "Non-Member"})

            fig_mem_rev = px.pie(
                mem_rev,
                names="Status", values="Revenue",
                hole=0.55,
                color_discrete_sequence=["#003399", "#ccd9ff"]
            )
            fig_mem_rev.update_traces(
                textinfo="label+percent",
                textfont_size=11,
                text=mem_rev["Revenue"].apply(format_naira)
            )
            fig_mem_rev.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=5, r=5, t=20, b=5),
                height=280
            )
            st.markdown(
                "<div class='section-title'>Revenue Split</div>",
                unsafe_allow_html=True
            )
            st.plotly_chart(fig_mem_rev, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # SECTION 5 — ACQUISITION CHANNEL BREAKDOWN
    # --------------------------------------------------------
    st.markdown(
        "<div class='section-title'>📣 Acquisition Channel Breakdown</div>",
        unsafe_allow_html=True
    )

    col3, col4 = st.columns(2)

    with col3:
        channel_counts = customers_df[
            customers_df["acquisition_channel"].notna()
        ]["acquisition_channel"].value_counts().reset_index()
        channel_counts.columns = ["Channel", "Customers"]

        if not channel_counts.empty:
            fig_channel = px.bar(
                channel_counts,
                x="Customers", y="Channel",
                orientation="h",
                text="Customers",
                color_discrete_sequence=["#003399"]
            )
            fig_channel.update_traces(textposition="outside", textfont_size=10)
            fig_channel.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=5, r=40, t=10, b=5),
                xaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
                yaxis=dict(showgrid=False, title=""),
                height=280
            )
            st.plotly_chart(fig_channel, use_container_width=True)
        else:
            st.info("No acquisition channel data yet.")

    with col4:
        # Deposit balance distribution
        deposit_customers = customers_df[customers_df["deposit_balance"] > 0]

        if not deposit_customers.empty:
            fig_deposit = px.histogram(
                deposit_customers,
                x="deposit_balance",
                nbins=20,
                color_discrete_sequence=["#003399"],
                title=""
            )
            fig_deposit.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=5, r=5, t=10, b=5),
                xaxis=dict(showgrid=True, gridcolor="#f0f0f0",
                           title="Deposit Balance (₦)"),
                yaxis=dict(showgrid=True, gridcolor="#f0f0f0",
                           title="Number of Customers"),
                height=280
            )
            st.markdown(
                "<div class='section-title'>💰 Deposit Balance Distribution</div>",
                unsafe_allow_html=True
            )
            st.plotly_chart(fig_deposit, use_container_width=True)
        else:
            st.info("No deposit balance data yet.")


# ============================================================
# RETENTION COHORT ANALYSIS
# For each month cohort of first-time customers,
# tracks how many are still ordering in subsequent months.
# ============================================================
def render_retention_cohort(orders_df):

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-title'>🔄 Retention Cohort Analysis</div>",
        unsafe_allow_html=True
    )
    st.markdown("""
        <p style='color:#666;font-size:13px;margin-bottom:16px;'>
        Each row shows a cohort of customers who placed their first order
        in that month. The columns show what % of those customers
        came back in months 1, 2, 3 etc after their first order.
        </p>
    """, unsafe_allow_html=True)

    # --------------------------------------------------------
    # BUILD COHORT TABLE
    # --------------------------------------------------------

    # Get each customer's first order date
    first_orders = orders_df.groupby("Customer Name")["Date of Order"].min().reset_index()
    first_orders.columns = ["Customer Name", "First Order Date"]
    first_orders["Cohort Month"] = first_orders["First Order Date"].dt.to_period("M")

    # Merge back to all orders
    cohort_df = orders_df.merge(first_orders, on="Customer Name")
    cohort_df["Order Month"] = cohort_df["Date of Order"].dt.to_period("M")
    cohort_df["Period Number"] = (
        cohort_df["Order Month"] - cohort_df["Cohort Month"]
    ).apply(lambda x: x.n)

    # Count unique customers per cohort per period
    cohort_counts = cohort_df.groupby(
        ["Cohort Month", "Period Number"]
    )["Customer Name"].nunique().reset_index()

    # Pivot into cohort table
    cohort_pivot = cohort_counts.pivot(
        index="Cohort Month", columns="Period Number", values="Customer Name"
    )

    # Convert to retention percentages
    cohort_size = cohort_pivot[0]
    retention = cohort_pivot.divide(cohort_size, axis=0) * 100

    # Format for display
    retention_display = retention.copy()
    for col in retention_display.columns:
        retention_display[col] = retention_display[col].apply(
            lambda x: f"{x:.0f}%" if pd.notna(x) else ""
        )

    retention_display.index = retention_display.index.astype(str)
    retention_display.columns = [
        f"Month {int(c)}" if c > 0 else "Month 0 (Base)"
        for c in retention_display.columns
    ]

    st.dataframe(retention_display, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Heatmap version
    st.markdown(
        "<div class='section-title'>🗺️ Retention Heatmap</div>",
        unsafe_allow_html=True
    )

    retention_vals = retention.copy()
    retention_vals.index = retention_vals.index.astype(str)

    fig_heat = go.Figure(data=go.Heatmap(
        z=retention_vals.values,
        x=[f"M+{int(c)}" for c in retention_vals.columns],
        y=retention_vals.index.tolist(),
        colorscale=[
            [0, "#fff0f0"],
            [0.3, "#ccd9ff"],
            [0.6, "#6699ff"],
            [1, "#003399"]
        ],
        text=[[f"{v:.0f}%" if pd.notna(v) else "" for v in row]
              for row in retention_vals.values],
        texttemplate="%{text}",
        textfont=dict(size=11, color="white"),
        showscale=True
    ))
    fig_heat.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis=dict(title="Months Since First Order"),
        yaxis=dict(title="Cohort Month"),
        height=350
    )
    st.plotly_chart(fig_heat, use_container_width=True)


# ============================================================
# PRODUCT FREQUENCY DEEP DIVE
# Average days between orders, early at-risk detection,
# top vs bottom frequency customers.
# ============================================================
def render_product_frequency(orders_df):

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-title'>⏱️ Product Frequency Deep Dive</div>",
        unsafe_allow_html=True
    )

    today = pd.Timestamp.now().normalize()

    # --------------------------------------------------------
    # CALCULATE DAYS BETWEEN ORDERS PER CUSTOMER
    # --------------------------------------------------------
    customer_orders = orders_df.sort_values(
        ["Customer Name", "Date of Order"]
    ).groupby("Customer Name").agg(
        Total_Orders=("Order ID", "count"),
        First_Order=("Date of Order", "min"),
        Last_Order=("Date of Order", "max"),
        Total_Revenue=("Revenue", "sum"),
        Products=("Order Type", lambda x: x.mode()[0] if len(x) > 0 else "Unknown")
    ).reset_index()

    # Days since last order
    customer_orders["Days Since Last Order"] = (
        today - customer_orders["Last_Order"]
    ).dt.days

    # Average days between orders
    customer_orders["Tenure Days"] = (
        customer_orders["Last_Order"] - customer_orders["First_Order"]
    ).dt.days
    customer_orders["Avg Days Between Orders"] = (
        customer_orders["Tenure Days"] /
        (customer_orders["Total_Orders"] - 1)
    ).where(customer_orders["Total_Orders"] > 1, None).round(1)

    # --------------------------------------------------------
    # EARLY AT-RISK DETECTION
    # Customers who haven't ordered in 14+ days
    # but are not yet in the 30-day churn threshold
    # --------------------------------------------------------
    early_risk = customer_orders[
        (customer_orders["Days Since Last Order"] >= 14) &
        (customer_orders["Days Since Last Order"] < 30)
    ].sort_values("Days Since Last Order", ascending=False)

    col1, col2, col3 = st.columns(3)

    with col1:
        avg_days_between = customer_orders[
            customer_orders["Avg Days Between Orders"].notna()
        ]["Avg Days Between Orders"].mean()
        st.metric(
            label="Avg Days Between Orders",
            value=f"{avg_days_between:.1f} days" if pd.notna(avg_days_between) else "N/A"
        )

    with col2:
        st.metric(
            label="Early At-Risk (14-30 days)",
            value=str(len(early_risk)),
            delta=f"-{len(early_risk)} need attention",
            delta_color="inverse"
        )

    with col3:
        repeat_customers = customer_orders[
            customer_orders["Total_Orders"] > 1
        ]
        st.metric(
            label="Repeat Customers",
            value=f"{len(repeat_customers):,}",
            delta=f"{(len(repeat_customers)/len(customer_orders)*100):.1f}% of base"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # EARLY AT-RISK TABLE
    # --------------------------------------------------------
    if not early_risk.empty:
        st.markdown(
            "<div class='section-title'>⚠️ Early At-Risk Customers (14-30 Days Silent)</div>",
            unsafe_allow_html=True
        )
        early_display = early_risk[[
            "Customer Name", "Days Since Last Order",
            "Total_Orders", "Total_Revenue", "Products"
        ]].copy()
        early_display["Total_Revenue"] = early_display["Total_Revenue"].apply(format_naira)
        early_display = early_display.rename(columns={
            "Customer Name": "Customer",
            "Days Since Last Order": "Days Silent",
            "Total_Orders": "Total Orders",
            "Total_Revenue": "Total Revenue",
            "Products": "Main Product"
        })
        st.dataframe(early_display, use_container_width=True, hide_index=True, height=280)

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # TOP VS BOTTOM FREQUENCY CUSTOMERS
    # --------------------------------------------------------
    col3, col4 = st.columns(2)

    freq_customers = customer_orders[
        customer_orders["Avg Days Between Orders"].notna()
    ].copy()

    with col3:
        st.markdown(
            "<div class='section-title'>🏆 Most Frequent Customers</div>",
            unsafe_allow_html=True
        )
        top_freq = freq_customers.nsmallest(10, "Avg Days Between Orders")[[
            "Customer Name", "Avg Days Between Orders",
            "Total_Orders", "Total_Revenue"
        ]].copy()
        top_freq["Total_Revenue"] = top_freq["Total_Revenue"].apply(format_naira)
        top_freq = top_freq.rename(columns={
            "Customer Name": "Customer",
            "Avg Days Between Orders": "Avg Days Between Orders",
            "Total_Orders": "Orders",
            "Total_Revenue": "Revenue"
        })
        st.dataframe(top_freq, use_container_width=True, hide_index=True)

    with col4:
        st.markdown(
            "<div class='section-title'>📉 Least Frequent Customers</div>",
            unsafe_allow_html=True
        )
        bottom_freq = freq_customers.nlargest(10, "Avg Days Between Orders")[[
            "Customer Name", "Avg Days Between Orders",
            "Total_Orders", "Total_Revenue"
        ]].copy()
        bottom_freq["Total_Revenue"] = bottom_freq["Total_Revenue"].apply(format_naira)
        bottom_freq = bottom_freq.rename(columns={
            "Customer Name": "Customer",
            "Avg Days Between Orders": "Avg Days Between Orders",
            "Total_Orders": "Orders",
            "Total_Revenue": "Revenue"
        })
        st.dataframe(bottom_freq, use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # ORDER FREQUENCY DISTRIBUTION CHART
    # --------------------------------------------------------
    st.markdown(
        "<div class='section-title'>📊 Order Frequency Distribution</div>",
        unsafe_allow_html=True
    )

    freq_dist = customer_orders["Total_Orders"].value_counts().reset_index()
    freq_dist.columns = ["Orders Count", "Customers"]
    freq_dist = freq_dist.sort_values("Orders Count")

    fig_dist = px.bar(
        freq_dist,
        x="Orders Count",
        y="Customers",
        text="Customers",
        color_discrete_sequence=["#003399"]
    )
    fig_dist.update_traces(textposition="outside", textfont_size=10)
    fig_dist.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=5, r=5, t=10, b=5),
        xaxis=dict(
            showgrid=False, title="Number of Orders",
            tickmode="linear"
        ),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title="Number of Customers"),
        height=300
    )
    st.plotly_chart(fig_dist, use_container_width=True)