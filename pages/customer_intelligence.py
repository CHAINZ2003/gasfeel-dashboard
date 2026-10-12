# ============================================================
# CUSTOMER INTELLIGENCE TAB — GasFeel Dashboard
# Deep customer analysis using enriched Supabase customers table.
# Shows membership, deposits, run-out dates, acquisition channels,
# retention cohorts, and product frequency analysis.
# All charts include descriptions for team readability.
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
# HELPER — LOAD CUSTOMER DATA FROM SUPABASE
# ============================================================
@st.cache_data(ttl=600)
def load_customer_intelligence():
    try:
        supabase = create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_KEY"]
        )

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

        date_cols = [
            "last_bought_date", "run_out_date",
            "next_reachout_date", "created_at"
        ]
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

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
# MAIN RENDER FUNCTION — CUSTOMER INTELLIGENCE
# ============================================================
def render_customer_intelligence(orders_df):

    today        = pd.Timestamp.now().normalize()
    customers_df = load_customer_intelligence()

    if customers_df.empty:
        st.info("No customer intelligence data available.")
        return

    # --------------------------------------------------------
    # CALCULATE SNAPSHOT METRICS
    # --------------------------------------------------------
    total_customers  = len(customers_df)
    active_customers = customers_df["is_active"].sum()
    member_customers = customers_df["is_member"].sum()
    total_deposit    = customers_df["deposit_balance"].sum()
    avg_deposit      = customers_df[
        customers_df["deposit_balance"] > 0
    ]["deposit_balance"].mean()

    running_out_soon = customers_df[
        (customers_df["run_out_date"] >= today) &
        (customers_df["run_out_date"] <= today + timedelta(days=7))
    ]
    reachout_due = customers_df[
        customers_df["next_reachout_date"].notna() &
        (customers_df["next_reachout_date"] <= today)
    ]
    mem_util = (
        customers_df["membership_deliveries_used"].sum() /
        customers_df["membership_deliveries_total"].sum() * 100
        if customers_df["membership_deliveries_total"].sum() > 0 else 0
    )

    # --------------------------------------------------------
    # SECTION 1 — SNAPSHOT KPIs
    # --------------------------------------------------------
    st.markdown(
        "<div class='section-title'>⚡ Customer Intelligence Snapshot</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "Live summary of your customer base from the Supabase database. "
        "Running Out Soon and Reachout Due are your most actionable numbers — "
        "these are customers who need to be contacted today."
    )

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
             "within 7 days",
             "#cc0000" if len(running_out_soon) > 10 else "#f0a500")
    with k5:
        snap("Reachout Due", f"{len(reachout_due):,}",
             "today or overdue", "#f0a500")
    with k6:
        snap("Membership Utilization", f"{mem_util:.1f}%",
             "deliveries used", "#003399")

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # SECTION 2 — RUNNING OUT SOON
    # --------------------------------------------------------
    st.markdown(
        "<div class='section-title'>🔴 Customers Running Out This Week — Call Now</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "Customers whose fuel or gas is expected to run out within 7 days. "
        "This is your highest-priority proactive sales list. "
        "Calling these customers before they run out increases conversion rate "
        "because they already know they need to reorder. "
        "Sorted by Days Until Empty — most urgent shown first."
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
        runout_display["run_out_date"]    = runout_display["run_out_date"].dt.strftime("%d %b %Y")
        runout_display["last_bought_date"] = runout_display["last_bought_date"].dt.strftime("%d %b %Y")
        runout_display = runout_display.rename(columns={
            "name":            "Customer",
            "whatsapp_number": "WhatsApp",
            "customer_type":   "Type",
            "usual_kg":        "Usual Qty",
            "run_out_date":    "Runs Out",
            "last_bought_date":"Last Order"
        })
        st.dataframe(runout_display, width="stretch", hide_index=True)
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
    chart_note(
        "Customers whose scheduled follow-up date has passed. "
        "These are contacts that agents planned to reach out to "
        "but have not yet done so. "
        "Days Overdue = how many days past the planned date. "
        "Longer overdue = higher risk of losing that customer."
    )

    if not reachout_due.empty:
        reachout_display = reachout_due[[
            "name", "whatsapp_number", "customer_type",
            "next_reachout_date", "last_bought_date", "owning_agent_id"
        ]].copy()
        reachout_display["Days Overdue"] = (
            today - reachout_display["next_reachout_date"]
        ).dt.days
        reachout_display = reachout_display.sort_values(
            "Days Overdue", ascending=False
        )
        reachout_display["next_reachout_date"] = reachout_display[
            "next_reachout_date"
        ].dt.strftime("%d %b %Y")
        reachout_display["last_bought_date"] = pd.to_datetime(
            reachout_display["last_bought_date"], errors="coerce"
        ).dt.strftime("%d %b %Y")
        reachout_display = reachout_display.rename(columns={
            "name":               "Customer",
            "whatsapp_number":    "WhatsApp",
            "customer_type":      "Type",
            "next_reachout_date": "Due Date",
            "last_bought_date":   "Last Order",
            "owning_agent_id":    "Agent"
        })
        st.dataframe(reachout_display, width="stretch", hide_index=True)
    else:
        st.success("No reachouts overdue today.")

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # SECTION 4 — MEMBER VS NON-MEMBER
    # --------------------------------------------------------
    st.markdown(
        "<div class='section-title'>👑 Member vs Non-Member Analysis</div>",
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            "<div class='section-title'>Customer Count</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Split between paying members and non-members. "
            "A growing member base means more predictable recurring revenue "
            "and lower churn risk since members have committed upfront."
        )

        member_counts = pd.DataFrame({
            "Status": ["Member", "Non-Member"],
            "Count":  [int(member_customers), int(total_customers - member_customers)]
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
        st.plotly_chart(fig_mem, width="stretch")

    with col2:
        st.markdown(
            "<div class='section-title'>Revenue Split</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Revenue contribution from members vs non-members. "
            "If members generate a disproportionately large revenue share, "
            "the membership programme is working well. "
            "If non-members dominate revenue, consider incentives "
            "to convert high-value non-members into members."
        )

        if "Customer Phone" in orders_df.columns:
            member_phones = set(
                customers_df[customers_df["is_member"] == True][
                    "whatsapp_number"
                ].astype(str).tolist()
            )
            orders_df["Is Member"] = orders_df[
                "Customer Phone"
            ].astype(str).isin(member_phones)
            mem_rev = orders_df.groupby("Is Member")["Revenue"].sum().reset_index()
            mem_rev["Status"] = mem_rev["Is Member"].map(
                {True: "Member", False: "Non-Member"}
            )
            fig_mem_rev = px.pie(
                mem_rev,
                names="Status", values="Revenue",
                hole=0.55,
                color_discrete_sequence=["#003399", "#ccd9ff"]
            )
            fig_mem_rev.update_traces(
                textinfo="label+percent", textfont_size=11
            )
            fig_mem_rev.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=5, r=5, t=20, b=5),
                height=280
            )
            st.plotly_chart(fig_mem_rev, width="stretch")

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # SECTION 5 — ACQUISITION CHANNEL + DEPOSIT DISTRIBUTION
    # --------------------------------------------------------
    st.markdown(
        "<div class='section-title'>📣 Acquisition & Deposit Analysis</div>",
        unsafe_allow_html=True
    )

    col3, col4 = st.columns(2)

    with col3:
        st.markdown(
            "<div class='section-title'>Acquisition Channel Breakdown</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "How customers first found or joined GasFeel. "
            "The longest bar is your most effective acquisition channel. "
            "Invest more in what is working and review channels "
            "that bring very few customers."
        )

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
            fig_channel.update_traces(
                textposition="outside",
                textfont=dict(size=10, color="#333333")
            )
            fig_channel.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=5, r=40, t=10, b=5),
                xaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
                yaxis=dict(showgrid=False, title=""),
                height=280
            )
            st.plotly_chart(fig_channel, width="stretch")
        else:
            st.info("No acquisition channel data yet.")

    with col4:
        st.markdown(
            "<div class='section-title'>💰 Deposit Balance Distribution</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "How deposit balances are distributed across customers. "
            "Most bars on the left = small deposits typical. "
            "Bars far right = high-value deposit holders — "
            "these customers have committed significant funds and "
            "are highly unlikely to churn."
        )

        deposit_customers = customers_df[customers_df["deposit_balance"] > 0]
        if not deposit_customers.empty:
            fig_deposit = px.histogram(
                deposit_customers,
                x="deposit_balance",
                nbins=20,
                color_discrete_sequence=["#003399"]
            )
            fig_deposit.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=5, r=5, t=10, b=5),
                xaxis=dict(
                    showgrid=True, gridcolor="#f0f0f0",
                    title="Deposit Balance (₦)"
                ),
                yaxis=dict(
                    showgrid=True, gridcolor="#f0f0f0",
                    title="Number of Customers"
                ),
                height=280
            )
            st.plotly_chart(fig_deposit, width="stretch")
        else:
            st.info("No deposit balance data yet.")


def render_retention_cohort(orders_df):

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-title'>🔄 Retention Cohort Analysis</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "Each row is a group of customers who placed their FIRST ever order "
        "in that month — called a cohort. "
        "The columns show how many of those customers came back "
        "in Month 1, Month 2, Month 3 after their first order. "
        "Month 0 always shows 100% because that is when they first ordered. "
        "Read it like this: 'Of the 45 customers who first ordered in January, "
        "28 (62%) came back in February, and 19 (42%) came back in March.' "
        "Higher numbers = stronger long-term retention."
    )

    # --------------------------------------------------------
    # BUILD COHORT DATA
    # --------------------------------------------------------
    first_orders = orders_df.groupby(
        "Customer Name"
    )["Date of Order"].min().reset_index()
    first_orders.columns   = ["Customer Name", "First Order Date"]
    first_orders["Cohort Month"] = first_orders["First Order Date"].dt.to_period("M")

    cohort_df = orders_df.merge(first_orders, on="Customer Name")
    cohort_df["Order Month"]   = cohort_df["Date of Order"].dt.to_period("M")
    cohort_df["Period Number"] = (
        cohort_df["Order Month"] - cohort_df["Cohort Month"]
    ).apply(lambda x: x.n)

    cohort_counts = cohort_df.groupby(
        ["Cohort Month", "Period Number"]
    )["Customer Name"].nunique().reset_index()
    cohort_counts.columns = ["Cohort Month", "Period", "Customers"]

    cohort_pivot = cohort_counts.pivot(
        index="Cohort Month", columns="Period", values="Customers"
    )

    cohort_size   = cohort_pivot[0]
    retention_pct = cohort_pivot.divide(cohort_size, axis=0) * 100

    # --------------------------------------------------------
    # DESCRIPTIVE TABLE — Numbers + % in each cell
    # --------------------------------------------------------
    st.markdown(
        "<div class='section-title'>📋 Month-on-Month Retention Table</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "Each cell shows: number of customers who returned / total in cohort (%). "
        "Example: '28/45 (62%)' means 28 out of 45 first-time customers "
        "from that month came back. "
        "Empty cells mean not enough time has passed yet."
    )

    descriptive_rows = []
    for cohort_month in cohort_pivot.index:
        row = {"Cohort Month": str(cohort_month)}
        cohort_total = int(cohort_size[cohort_month])
        row["Cohort Size"] = f"{cohort_total} customers"

        for period in cohort_pivot.columns:
            count = cohort_pivot.loc[cohort_month, period]
            pct   = retention_pct.loc[cohort_month, period]
            if pd.notna(count):
                count = int(count)
                if period == 0:
                    row[f"Month 0 (Start)"] = f"{count} (100%)"
                else:
                    row[f"Month +{int(period)}"] = f"{count}/{cohort_total} ({pct:.0f}%)"
            else:
                if period == 0:
                    row["Month 0 (Start)"] = ""
                else:
                    row[f"Month +{int(period)}"] = ""

        descriptive_rows.append(row)

    descriptive_df = pd.DataFrame(descriptive_rows)
    descriptive_df = descriptive_df.set_index("Cohort Month")

    st.dataframe(descriptive_df, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # HEATMAP — Visual version
    # --------------------------------------------------------
    st.markdown(
        "<div class='section-title'>🗺️ Retention Heatmap</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "Same data shown as a colour heatmap. "
        "Each cell shows the retention % and the actual customer count. "
        "Dark blue = strong retention. Light = weak. Empty = no data yet. "
        "Read each row left to right — this shows how quickly "
        "customers from each month stopped coming back."
    )

    retention_vals = retention_pct.copy()
    retention_vals.index = retention_vals.index.astype(str)

    # Build hover text with both count and percentage
    hover_text = []
    for cohort_month in cohort_pivot.index:
        row_text = []
        cohort_total = int(cohort_size[cohort_month])
        for period in cohort_pivot.columns:
            count = cohort_pivot.loc[cohort_month, period]
            pct   = retention_pct.loc[cohort_month, period]
            if pd.notna(count):
                row_text.append(
                    f"{int(count)} of {cohort_total} customers ({pct:.0f}%)"
                )
            else:
                row_text.append("")
        hover_text.append(row_text)

    # Cell labels showing both count and %
    cell_labels = []
    for cohort_month in cohort_pivot.index:
        row_labels = []
        cohort_total = int(cohort_size[cohort_month])
        for period in cohort_pivot.columns:
            count = cohort_pivot.loc[cohort_month, period]
            pct   = retention_pct.loc[cohort_month, period]
            if pd.notna(count):
                row_labels.append(f"{int(count)}\n({pct:.0f}%)")
            else:
                row_labels.append("")
        cell_labels.append(row_labels)

    fig_heat = go.Figure(data=go.Heatmap(
        z=retention_vals.values,
        x=[f"Month 0 (Start)" if c == 0 else f"Month +{int(c)}"
           for c in retention_vals.columns],
        y=retention_vals.index.tolist(),
        colorscale=[
            [0,   "#fff0f0"],
            [0.3, "#ccd9ff"],
            [0.6, "#6699ff"],
            [1,   "#003399"]
        ],
        text=cell_labels,
        texttemplate="%{text}",
        textfont=dict(size=10, color="white"),
        hovertext=hover_text,
        hovertemplate="%{hovertext}<extra></extra>",
        showscale=True
    ))
    fig_heat.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis=dict(title="Months Since First Order"),
        yaxis=dict(title="Cohort Month"),
        height=400
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    # --------------------------------------------------------
    # WEEK BY WEEK RETENTION TABLE
    # --------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-title'>📅 Week-by-Week Retention Table</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "Same cohort analysis but broken down by week instead of month. "
        "Each row = customers who ordered for the FIRST time in that week. "
        "Each column shows how many came back in Week +1, Week +2 etc. "
        "Read it like: '12/20 (60%) means 12 out of 20 customers "
        "who first ordered in that week came back the following week.' "
        "Use this for faster feedback on retention trends than monthly view."
    )

    # Build weekly cohort
    first_orders_wk = orders_df.groupby(
        "Customer Name"
    )["Date of Order"].min().reset_index()
    first_orders_wk.columns = ["Customer Name", "First Order Date"]
    first_orders_wk["Cohort Week"] = first_orders_wk[
        "First Order Date"
    ].dt.to_period("W")

    cohort_wk = orders_df.merge(first_orders_wk, on="Customer Name")
    cohort_wk["Order Week"]     = cohort_wk["Date of Order"].dt.to_period("W")
    cohort_wk["Period Number"]  = (
        cohort_wk["Order Week"] - cohort_wk["Cohort Week"]
    ).apply(lambda x: x.n)

    # Only keep up to Week +8 to keep table readable
    cohort_wk = cohort_wk[cohort_wk["Period Number"] <= 8]

    wk_counts = cohort_wk.groupby(
        ["Cohort Week", "Period Number"]
    )["Customer Name"].nunique().reset_index()
    wk_counts.columns = ["Cohort Week", "Period", "Customers"]

    wk_pivot = wk_counts.pivot(
        index="Cohort Week", columns="Period", values="Customers"
    )

    wk_size   = wk_pivot[0]
    wk_pct    = wk_pivot.divide(wk_size, axis=0) * 100

    # Build descriptive weekly table
    wk_rows = []
    for cohort_week in wk_pivot.index:
        row = {
            "Cohort Week": str(cohort_week),
            "Cohort Size": f"{int(wk_size[cohort_week])} customers"
        }
        total = int(wk_size[cohort_week])
        for period in wk_pivot.columns:
            count = wk_pivot.loc[cohort_week, period]
            pct   = wk_pct.loc[cohort_week, period]
            if pd.notna(count):
                count = int(count)
                if period == 0:
                    row["Week 0 (First Order)"] = f"{count} (100%)"
                else:
                    row[f"Week +{int(period)}"] = f"{count}/{total} ({pct:.0f}%)"
            else:
                if period == 0:
                    row["Week 0 (First Order)"] = ""
                else:
                    row[f"Week +{int(period)}"] = ""
        wk_rows.append(row)

    wk_display = pd.DataFrame(wk_rows).set_index("Cohort Week")

    # Only show last 12 weeks to keep readable
    wk_display = wk_display.tail(12)

    st.dataframe(wk_display, use_container_width=True)

    # --------------------------------------------------------
    # WEEK BY WEEK HEATMAP
    # --------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-title'>🗺️ Weekly Retention Heatmap</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "Visual version of the weekly cohort table. "
        "Each cell shows customer count and retention %. "
        "Dark blue = strong week-on-week retention. "
        "Fading quickly = customers are not coming back the following week. "
        "Consistent dark blue across a row = highly loyal cohort."
    )

    wk_vals = wk_pct.copy()
    wk_vals.index = wk_vals.index.astype(str)
    wk_vals = wk_vals.tail(12)
    wk_pivot_disp = wk_pivot.loc[wk_pivot.index[-12:]] if len(wk_pivot) > 12 else wk_pivot

    wk_cell_labels = []
    for cohort_week in wk_pivot_disp.index:
        row_labels = []
        total = int(wk_size[cohort_week])
        for period in wk_pivot_disp.columns:
            count = wk_pivot_disp.loc[cohort_week, period]
            pct   = wk_pct.loc[cohort_week, period]
            if pd.notna(count):
                row_labels.append(f"{int(count)}\n({pct:.0f}%)")
            else:
                row_labels.append("")
        wk_cell_labels.append(row_labels)

    fig_wk_heat = go.Figure(data=go.Heatmap(
        z=wk_vals.values,
        x=["Week 0 (First)" if c == 0 else f"Week +{int(c)}"
           for c in wk_vals.columns],
        y=wk_vals.index.tolist(),
        colorscale=[
            [0,   "#fff0f0"],
            [0.3, "#ccd9ff"],
            [0.6, "#6699ff"],
            [1,   "#003399"]
        ],
        text=wk_cell_labels,
        texttemplate="%{text}",
        textfont=dict(size=10, color="white"),
        showscale=True
    ))
    fig_wk_heat.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis=dict(title="Weeks Since First Order"),
        yaxis=dict(title="Cohort Week"),
        height=420
    )
    st.plotly_chart(fig_wk_heat, use_container_width=True)

# ============================================================
# PRODUCT FREQUENCY DEEP DIVE
# ============================================================
def render_product_frequency(orders_df):

    today = pd.Timestamp.now().normalize()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-title'>⏱️ Product Frequency Deep Dive</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "How frequently customers reorder. "
        "Avg Days Between Orders = how long the typical customer waits before reordering. "
        "Lower = more engaged customers. Higher = customers are spacing out orders "
        "or buying from competitors between GasFeel orders."
    )

    customer_orders = orders_df.sort_values(
        ["Customer Name", "Date of Order"]
    ).groupby("Customer Name").agg(
        Total_Orders=("Order ID", "count"),
        First_Order=("Date of Order", "min"),
        Last_Order=("Date of Order", "max"),
        Total_Revenue=("Revenue", "sum"),
        Products=("Order Type", lambda x: x.mode()[0] if len(x) > 0 else "Unknown")
    ).reset_index()

    customer_orders["Days Since Last Order"] = (
        today - customer_orders["Last_Order"]
    ).dt.days
    customer_orders["Tenure Days"] = (
        customer_orders["Last_Order"] - customer_orders["First_Order"]
    ).dt.days
    customer_orders["Avg Days Between Orders"] = (
        customer_orders["Tenure Days"] /
        (customer_orders["Total_Orders"] - 1)
    ).where(customer_orders["Total_Orders"] > 1, None).round(1)

    # Early at-risk: 14-30 days silent
    early_risk = customer_orders[
        (customer_orders["Days Since Last Order"] >= 14) &
        (customer_orders["Days Since Last Order"] < 30)
    ].sort_values("Days Since Last Order", ascending=False)

    col1, col2, col3 = st.columns(3)

    avg_days = customer_orders[
        customer_orders["Avg Days Between Orders"].notna()
    ]["Avg Days Between Orders"].mean()

    with col1:
        st.metric(
            label="Avg Days Between Orders",
            value=f"{avg_days:.1f} days" if pd.notna(avg_days) else "N/A"
        )
    with col2:
        st.metric(
            label="Early At-Risk (14-30 days)",
            value=str(len(early_risk)),
            delta=f"-{len(early_risk)} need attention",
            delta_color="inverse"
        )
    with col3:
        repeat = customer_orders[customer_orders["Total_Orders"] > 1]
        st.metric(
            label="Repeat Customers",
            value=f"{len(repeat):,}",
            delta=f"{(len(repeat)/len(customer_orders)*100):.1f}% of base"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Early At-Risk Table
    if not early_risk.empty:
        st.markdown(
            "<div class='section-title'>⚠️ Early At-Risk Customers (14-30 Days Silent)</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Customers who have not ordered in 14-30 days. "
            "They are not yet in the official 'At Risk' category (30 days) "
            "but are showing early signs of disengagement. "
            "A proactive call now is much easier than a re-engagement "
            "campaign after they have fully churned."
        )
        early_display = early_risk[[
            "Customer Name", "Days Since Last Order",
            "Total_Orders", "Total_Revenue", "Products"
        ]].copy()
        early_display["Total_Revenue"] = early_display["Total_Revenue"].apply(format_naira)
        early_display = early_display.rename(columns={
            "Customer Name":        "Customer",
            "Days Since Last Order":"Days Silent",
            "Total_Orders":         "Total Orders",
            "Total_Revenue":        "Total Revenue",
            "Products":             "Main Product"
        })
        st.dataframe(
            early_display, width="stretch",
            hide_index=True, height=280
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Top vs Bottom Frequency
    col3, col4 = st.columns(2)
    freq_customers = customer_orders[
        customer_orders["Avg Days Between Orders"].notna()
    ].copy()

    with col3:
        st.markdown(
            "<div class='section-title'>🏆 Most Frequent Customers</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Customers with the shortest average time between orders. "
            "These are your most loyal and engaged customers. "
            "They deserve priority service, loyalty rewards, "
            "and first access to promotions."
        )
        top_freq = freq_customers.nsmallest(10, "Avg Days Between Orders")[[
            "Customer Name", "Avg Days Between Orders",
            "Total_Orders", "Total_Revenue"
        ]].copy()
        top_freq["Total_Revenue"] = top_freq["Total_Revenue"].apply(format_naira)
        top_freq = top_freq.rename(columns={
            "Customer Name":           "Customer",
            "Avg Days Between Orders": "Avg Days Between Orders",
            "Total_Orders":            "Orders",
            "Total_Revenue":           "Revenue"
        })
        st.dataframe(top_freq, width="stretch", hide_index=True)

    with col4:
        st.markdown(
            "<div class='section-title'>📉 Least Frequent Customers</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Customers with the longest average gap between orders. "
            "They may be using GasFeel only occasionally or "
            "splitting orders between GasFeel and competitors. "
            "Target these customers with frequency incentives — "
            "discounts for ordering twice in one week for example."
        )
        bottom_freq = freq_customers.nlargest(10, "Avg Days Between Orders")[[
            "Customer Name", "Avg Days Between Orders",
            "Total_Orders", "Total_Revenue"
        ]].copy()
        bottom_freq["Total_Revenue"] = bottom_freq["Total_Revenue"].apply(format_naira)
        bottom_freq = bottom_freq.rename(columns={
            "Customer Name":           "Customer",
            "Avg Days Between Orders": "Avg Days Between Orders",
            "Total_Orders":            "Orders",
            "Total_Revenue":           "Revenue"
        })
        st.dataframe(bottom_freq, width="stretch", hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Order Frequency Distribution
    st.markdown(
        "<div class='section-title'>📊 Order Frequency Distribution</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "How many customers have placed 1, 2, 3, 4+ orders in total. "
        "A tall bar at 1 means most customers only ordered once — "
        "a retention problem. Growing bars at 3, 4, 5+ means "
        "customers are becoming loyal repeat buyers."
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
    fig_dist.update_traces(
        textposition="outside",
        textfont=dict(size=10, color="#333333")
    )
    fig_dist.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=5, r=5, t=10, b=5),
        xaxis=dict(
            showgrid=False, title="Number of Orders",
            tickmode="linear"
        ),
        yaxis=dict(
            showgrid=True, gridcolor="#f0f0f0",
            title="Number of Customers"
        ),
        height=300
    )
    st.plotly_chart(fig_dist, width="stretch")