# ============================================================
# AGENT PERFORMANCE TAB — GasFeel Dashboard
# Shows agent activity, conversion rates, revenue and
# commission earned. Pulls from Supabase interactions table.
# All charts include descriptions for team readability.
# ============================================================

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
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
# HELPER — LOAD AGENT DATA FROM SUPABASE
# ============================================================
@st.cache_data(ttl=600)
def load_agent_data():
    try:
        supabase = create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_KEY"]
        )

        all_interactions = []
        offset = 0
        while True:
            result = supabase.table("interactions").select(
                "id,agent_id,agent_name,submitted_at,outcome,"
                "product,quantity,revenue,commission_earned,"
                "commission_rate_applied,order_total,source,"
                "customer_whatsapp"
            ).range(offset, offset + 999).execute()
            if not result.data:
                break
            all_interactions.extend(result.data)
            if len(result.data) < 1000:
                break
            offset += 1000

        if not all_interactions:
            return pd.DataFrame(), pd.DataFrame()

        interactions_df = pd.DataFrame(all_interactions)
        interactions_df = interactions_df.dropna(subset=["submitted_at"])
        interactions_df["submitted_at"] = pd.to_datetime(
            interactions_df["submitted_at"],
            errors="coerce", utc=True
        )
        interactions_df["Date"]       = interactions_df["submitted_at"].dt.date
        interactions_df["Month"]      = interactions_df["submitted_at"].dt.month
        interactions_df["Month Name"] = interactions_df["submitted_at"].dt.strftime("%B")
        interactions_df["Year"]       = interactions_df["submitted_at"].dt.year
        interactions_df["Week"]       = interactions_df[
            "submitted_at"
        ].dt.isocalendar().week.astype("Int64")

        interactions_df["revenue"] = pd.to_numeric(
            interactions_df["revenue"], errors="coerce"
        ).fillna(0)
        interactions_df["commission_earned"] = pd.to_numeric(
            interactions_df["commission_earned"], errors="coerce"
        ).fillna(0)

        # Fetch agent profiles
        profiles_result = supabase.table("profiles").select(
            "agent_id,full_name,role,commission_rate_per_kg,"
            "commission_rate_per_litre,is_active,commission_cycle_start"
        ).execute()
        profiles_df = pd.DataFrame(
            profiles_result.data
        ) if profiles_result.data else pd.DataFrame()

        return interactions_df, profiles_df

    except Exception as e:
        st.error(f"Failed to load agent data: {e}")
        return pd.DataFrame(), pd.DataFrame()


# ============================================================
# MAIN RENDER FUNCTION — AGENT PERFORMANCE
# ============================================================
def render_agent(filtered_df):

    interactions_df, profiles_df = load_agent_data()

    if interactions_df.empty:
        st.info("No agent interaction data available yet.")
        return

    # Filter interactions to match selected months from sidebar
    selected_months = filtered_df["Month"].unique().tolist()
    interactions_filtered = interactions_df[
        interactions_df["Month"].isin(selected_months)
    ]

    # --------------------------------------------------------
    # CALCULATE TOP-LINE AGENT KPIs
    # --------------------------------------------------------
    total_interactions       = len(interactions_filtered)
    total_agents             = interactions_filtered["agent_id"].nunique()
    sales_interactions       = interactions_filtered[
        interactions_filtered["outcome"] == "sale"
    ]
    total_sales              = len(sales_interactions)
    conversion_rate          = (
        total_sales / total_interactions * 100
    ) if total_interactions > 0 else 0
    total_agent_revenue      = sales_interactions["revenue"].sum()
    total_commission         = interactions_filtered["commission_earned"].sum()
    unique_customers_reached = interactions_filtered["customer_whatsapp"].nunique()

    # --------------------------------------------------------
    # TOP KPI ROW
    # --------------------------------------------------------
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
        snap("Total Interactions", f"{total_interactions:,}",
             "all outcomes", "#003399")
    with k2:
        snap("Active Agents", str(total_agents),
             "this period", "#003399")
    with k3:
        snap("Total Sales", f"{total_sales:,}",
             "outcome = sale", "#00aa44")
    with k4:
        snap("Conversion Rate", f"{conversion_rate:.1f}%",
             "sales ÷ interactions",
             "#00aa44" if conversion_rate >= 30 else "#f0a500")
    with k5:
        snap("Agent Revenue", format_naira(total_agent_revenue),
             "from sales", "#003399")
    with k6:
        snap("Commission Paid", format_naira(total_commission),
             "total earned", "#003399")

    st.markdown("""
        <p style='color:#888;font-size:12px;font-style:italic;margin:4px 0 16px 0;'>
            💡 An interaction is any contact an agent logs with a customer —
            whether it results in a sale or not.
            Conversion Rate = Sales ÷ Total Interactions.
            Target conversion rate is 30% or above.
            Agent Revenue is the revenue GasFeel earned from agent-driven sales.
            Commission Paid is what agents earned from those sales.
        </p>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # ROW 2 — Leaderboard | Outcome Breakdown
    # --------------------------------------------------------
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            "<div class='section-title'>🏆 Agent Leaderboard</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Full performance table for every agent. "
            "Sorted by Revenue Generated — the agent driving the most "
            "revenue to GasFeel sits at the top. "
            "Conv % = Conversion Rate — how many of their interactions "
            "turned into actual sales. High interactions with low conv % "
            "means the agent is active but needs better closing skills."
        )

        agent_summary = interactions_filtered.groupby("agent_name").agg(
            Total=("id", "count"),
            Sales=("outcome", lambda x: (x == "sale").sum()),
            Revenue=("revenue", "sum"),
            Commission=("commission_earned", "sum")
        ).reset_index()
        agent_summary["Conversion %"] = (
            agent_summary["Sales"] / agent_summary["Total"] * 100
        ).round(1)
        agent_summary = agent_summary.sort_values("Revenue", ascending=False)

        st.dataframe(
            agent_summary.rename(columns={
                "agent_name":   "Agent",
                "Total":        "Interactions",
                "Sales":        "Sales",
                "Revenue":      "Revenue (₦)",
                "Commission":   "Commission (₦)",
                "Conversion %": "Conv %"
            }).style.format({
                "Revenue (₦)":    "₦{:,.0f}",
                "Commission (₦)": "₦{:,.0f}",
                "Conv %":         "{:.1f}%"
            }),
            use_container_width=True,
            hide_index=True,
            height=320
        )

    with col2:
        st.markdown(
            "<div class='section-title'>📊 Interaction Outcomes</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Breakdown of what happened in each agent interaction. "
            "Sale = customer bought. Lead = potential customer identified. "
            "No Sale = customer declined. Callback = follow-up scheduled. "
            "A healthy funnel has a large sale slice and manageable "
            "lead and callback sections that convert over time."
        )

        outcome_counts = interactions_filtered[
            "outcome"
        ].value_counts().reset_index()
        outcome_counts.columns = ["Outcome", "Count"]

        color_map = {
            "sale":     "#003399",
            "lead":     "#6699ff",
            "no_sale":  "#cc0000",
            "callback": "#f0a500",
            "other":    "#ccd9ff"
        }

        fig_outcome = px.pie(
            outcome_counts,
            names="Outcome",
            values="Count",
            hole=0.55,
            color="Outcome",
            color_discrete_map=color_map
        )
        fig_outcome.update_traces(
            textinfo="label+value+percent",
            textfont_size=11
        )
        fig_outcome.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=5, r=5, t=20, b=5),
            showlegend=True,
            height=320
        )
        st.plotly_chart(fig_outcome, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # ROW 3 — Conversion Rate | Weekly Activity Trend
    # --------------------------------------------------------
    col3, col4 = st.columns(2)

    with col3:
        st.markdown(
            "<div class='section-title'>🎯 Conversion Rate by Agent</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Each bar shows one agent's conversion rate. "
            "Green = at or above 30% target. "
            "Amber = 15-30% — room for improvement. "
            "Red = below 15% — needs coaching or script review. "
            "The dashed line marks the 30% benchmark."
        )

        agent_conv = agent_summary.sort_values("Conversion %", ascending=True)
        agent_conv["Color"] = agent_conv["Conversion %"].apply(
            lambda x: "#00aa44" if x >= 30 else ("#f0a500" if x >= 15 else "#cc0000")
        )

        fig_conv = go.Figure()
        fig_conv.add_trace(go.Bar(
            x=agent_conv["Conversion %"],
            y=agent_conv["agent_name"],
            orientation="h",
            marker_color=agent_conv["Color"],
            text=agent_conv["Conversion %"].apply(lambda x: f"{x:.1f}%"),
            textposition="outside",
            textfont=dict(size=10, color="#333333")
        ))
        fig_conv.add_vline(
            x=30, line_dash="dash", line_color="#003399",
            annotation_text="30% target",
            annotation_position="top right"
        )
        fig_conv.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=5, r=60, t=20, b=5),
            xaxis=dict(showgrid=True, gridcolor="#f0f0f0", title="%"),
            yaxis=dict(showgrid=False, title=""),
            height=320
        )
        st.plotly_chart(fig_conv, use_container_width=True)

    with col4:
        st.markdown(
            "<div class='section-title'>📈 Weekly Activity Trend</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Total interactions and sales closed each week. "
            "Blue bars = total interactions logged by all agents. "
            "Dark bars = sales that resulted from those interactions. "
            "Rising blue with rising dark = agents are getting more active "
            "and more effective. Rising blue with flat dark = "
            "more activity but conversion is not improving."
        )

        weekly = interactions_filtered.groupby("Week").agg(
            Interactions=("id", "count"),
            Sales=("outcome", lambda x: (x == "sale").sum())
        ).reset_index().sort_values("Week")
        weekly["Week Label"] = "WK" + weekly["Week"].astype(str)

        fig_weekly = go.Figure()
        fig_weekly.add_trace(go.Bar(
            name="Interactions",
            x=weekly["Week Label"],
            y=weekly["Interactions"],
            marker_color="#ccd9ff",
            text=weekly["Interactions"],
            textposition="outside",
            textfont=dict(size=10, color="#333333")
        ))
        fig_weekly.add_trace(go.Bar(
            name="Sales",
            x=weekly["Week Label"],
            y=weekly["Sales"],
            marker_color="#003399",
            text=weekly["Sales"],
            textposition="outside",
            textfont=dict(size=10, color="#333333")
        ))
        fig_weekly.update_layout(
            barmode="group",
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=5, r=5, t=20, b=5),
            xaxis=dict(showgrid=False, title=""),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            legend=dict(
                orientation="h",
                yanchor="bottom", y=1.02,
                xanchor="right", x=1
            ),
            height=320
        )
        st.plotly_chart(fig_weekly, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # ROW 4 — Revenue by Agent | Commission by Agent
    # --------------------------------------------------------
    col5, col6 = st.columns(2)

    with col5:
        st.markdown(
            "<div class='section-title'>💰 Revenue by Agent</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Total revenue GasFeel earned from each agent's sales. "
            "The longest bar is the agent generating the most business value. "
            "Compare this with the Commission chart — an agent with high revenue "
            "but high commission cost may need rate review."
        )

        agent_rev = agent_summary.sort_values("Revenue", ascending=True)
        fig_rev   = px.bar(
            agent_rev,
            x="Revenue",
            y="agent_name",
            orientation="h",
            text=agent_rev["Revenue"].apply(format_naira),
            color_discrete_sequence=["#003399"]
        )
        fig_rev.update_traces(
            textposition="outside",
            textfont=dict(size=10, color="#333333")
        )
        fig_rev.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=5, r=80, t=20, b=5),
            xaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            yaxis=dict(showgrid=False, title=""),
            height=320
        )
        st.plotly_chart(fig_rev, use_container_width=True)

    with col6:
        st.markdown(
            "<div class='section-title'>🤝 Commission Earned by Agent</div>",
            unsafe_allow_html=True
        )
        chart_note(
            "Total commission earned by each agent in the selected period. "
            "This is what GasFeel has paid out or owes each agent. "
            "High commission with high revenue = efficient agent. "
            "High commission with low revenue = may need rate renegotiation."
        )

        agent_comm = agent_summary.sort_values("Commission", ascending=True)
        fig_comm   = px.bar(
            agent_comm,
            x="Commission",
            y="agent_name",
            orientation="h",
            text=agent_comm["Commission"].apply(format_naira),
            color_discrete_sequence=["#00aa44"]
        )
        fig_comm.update_traces(
            textposition="outside",
            textfont=dict(size=10, color="#333333")
        )
        fig_comm.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=5, r=80, t=20, b=5),
            xaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
            yaxis=dict(showgrid=False, title=""),
            height=320
        )
        st.plotly_chart(fig_comm, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # FULL AGENT DETAIL TABLE
    # --------------------------------------------------------
    st.markdown(
        "<div class='section-title'>📋 Full Agent Activity Detail</div>",
        unsafe_allow_html=True
    )
    chart_note(
        "Complete summary of every agent's performance "
        "for the selected period. "
        "Use this table for performance reviews, "
        "commission calculations, and target setting. "
        "Conversion Rate = Sales Closed ÷ Total Interactions × 100."
    )

    detail = agent_summary.copy()
    detail["Revenue"]      = detail["Revenue"].apply(format_naira)
    detail["Commission"]   = detail["Commission"].apply(format_naira)
    detail["Conversion %"] = detail["Conversion %"].astype(str) + "%"
    detail = detail.rename(columns={
        "agent_name":   "Agent",
        "Total":        "Total Interactions",
        "Sales":        "Sales Closed",
        "Revenue":      "Revenue Generated",
        "Commission":   "Commission Earned",
        "Conversion %": "Conversion Rate"
    })

    st.dataframe(
        detail[[
            "Agent", "Total Interactions", "Sales Closed",
            "Conversion Rate", "Revenue Generated", "Commission Earned"
        ]],
        use_container_width=True,
        hide_index=True
    )