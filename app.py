# ============================================================
# APP.PY — GasFeel Dashboard Main Entry Point
# This is the file Streamlit runs first.
# Controls page config, styling, sidebar filters, and navigation.
# ============================================================

import streamlit as st
import os
from data_loader import load_orders, load_targets
from auth import is_authenticated, show_login, logout
# ============================================================
# PAGE CONFIGURATION
# Must be the very first Streamlit command in the file.
# ============================================================
st.set_page_config(
    page_title="GasFeel Dashboard",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# AUTHENTICATION GATE
# If user is not logged in, show login page and stop here.
# Nothing below this runs until the user is authenticated.
# ============================================================
if not is_authenticated():
    show_login()
    st.stop()

# ============================================================
# GLOBAL CSS STYLING
# All visual styling lives here.
# Edit only this section when changing colours or spacing.
# ============================================================
st.markdown("""
    <style>

    /* ============================================
       GLOBAL — Base background and font
    ============================================ */
    .stApp {
        background-color: #f0f4ff;
        font-family: 'Segoe UI', sans-serif;
    }

    /* ============================================
       SIDEBAR — Deep blue gradient
    ============================================ */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #001f6e 0%, #003399 60%, #0044cc 100%);
        border-right: 1px solid rgba(255,255,255,0.1);
    }

    /* Hide default Streamlit page navigation */
    [data-testid="stSidebarNav"] {
        display: none;
    }

    /* Sidebar text */
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: white !important;
    }

    /* Sidebar checkbox label */
    [data-testid="stSidebar"] .stCheckbox label p {
        color: white !important;
        font-size: 13px !important;
    }

    /* Sidebar checkbox tick colour */
    [data-testid="stSidebar"] .stCheckbox input[type="checkbox"] {
        accent-color: #ffffff;
    }

    /* Sidebar filter header */
    [data-testid="stSidebar"] strong {
        color: #a0c4ff !important;
        font-size: 10px !important;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        display: block;
        margin: 16px 0 8px 0;
    }

    /* Sidebar checkbox row spacing */
    [data-testid="stSidebar"] .stCheckbox {
        margin-bottom: 4px;
        padding: 4px 0;
        border-bottom: 1px solid rgba(255,255,255,0.07);
    }

    /* Sidebar buttons — Select All / Clear All */
    [data-testid="stSidebar"] .stButton button {
        background: rgba(255,255,255,0.15);
        color: white !important;
        border: 1px solid rgba(255,255,255,0.3);
        border-radius: 6px;
        font-size: 11px;
        padding: 4px 8px;
        width: 100%;
        font-weight: 600;
        margin-bottom: 8px;
    }

    [data-testid="stSidebar"] .stButton button:hover {
        background: rgba(255,255,255,0.25);
        border-color: white;
    }

    /* ============================================
       HEADER BAR
    ============================================ */
    .gasfeel-header {
        background: linear-gradient(135deg, #001f6e 0%, #003399 100%);
        padding: 18px 28px;
        border-radius: 12px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 4px 15px rgba(0,51,153,0.3);
    }

    .gasfeel-header h1 {
        color: white !important;
        font-size: 22px;
        margin: 0;
        font-weight: 700;
        letter-spacing: 0.5px;
    }

    .gasfeel-header span {
        background: rgba(255,255,255,0.15);
        color: white !important;
        font-size: 13px;
        padding: 5px 14px;
        border-radius: 20px;
        font-weight: 500;
    }

    /* ============================================
       ST.METRIC — Styled to match KPI card design
       Used for all indicator cards (green/red arrows)
    ============================================ */
    [data-testid="stMetric"] {
        background: white;
        border-radius: 14px;
        padding: 16px 20px !important;
        box-shadow: 0 4px 16px rgba(0,51,153,0.10);
        border-left: 5px solid #003399;
        margin-bottom: 14px;
    }

    [data-testid="stMetricLabel"] {
        color: #999999 !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    [data-testid="stMetricLabel"] p {
        color: #999999 !important;
        font-size: 11px !important;
        font-weight: 700 !important;
    }

    [data-testid="stMetricValue"] {
        color: #001f6e !important;
        font-size: 26px !important;
        font-weight: 800 !important;
    }

    [data-testid="stMetricValue"] div {
        color: #001f6e !important;
        font-size: 26px !important;
        font-weight: 800 !important;
    }

    /* Delta text size and weight */
    [data-testid="stMetricDelta"] {
        font-size: 15px !important;
        font-weight: 700 !important;
    }

    /* Hide the small triangle svg icon from delta */
    [data-testid="stMetricDelta"] svg {
        display: none !important;
    }

    /* ============================================
       KPI CARDS — For plain value cards (no delta)
    ============================================ */
    .kpi-card {
        background: white;
        border-radius: 14px;
        padding: 20px 22px;
        box-shadow: 0 4px 16px rgba(0,51,153,0.10);
        border-left: 5px solid #003399;
        margin-bottom: 14px;
    }

    .kpi-label {
        color: #999999;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }

    .kpi-value {
        color: #001f6e;
        font-size: 30px;
        font-weight: 800;
        line-height: 1.1;
    }

    /* ============================================
       SECTION TITLES — Above each chart or KPI group
    ============================================ */
    .section-title {
        color: #003399;
        font-size: 13px;
        font-weight: 700;
        margin-bottom: 10px;
        padding-bottom: 6px;
        border-bottom: 2px solid #e8eeff;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* ============================================
       TABS — Clean active state
    ============================================ */
    .stTabs [data-baseweb="tab-list"] {
        background-color: white;
        border-radius: 12px;
        padding: 5px;
        gap: 4px;
        box-shadow: 0 2px 8px rgba(0,51,153,0.08);
        margin-bottom: 20px;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        color: #003399 !important;
        font-weight: 600;
        font-size: 13px;
        border-radius: 8px;
        padding: 8px 18px;
        border: none;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #003399, #0044cc) !important;
        color: white !important;
        box-shadow: 0 2px 8px rgba(0,51,153,0.3);
    }

    /* ============================================
       PLOTLY — Force dark text on all chart labels
    ============================================ */
    .js-plotly-plot .plotly .xtick text,
    .js-plotly-plot .plotly .ytick text,
    .js-plotly-plot .plotly .gtitle,
    .js-plotly-plot .plotly .legendtext,
    .js-plotly-plot .plotly .annotation-text,
    .js-plotly-plot .plotly text {
        fill: #333333 !important;
        color: #333333 !important;
    }

    /* ============================================
       MAIN CONTENT — Padding and max width
    ============================================ */
    .main .block-container {
        padding: 20px 28px !important;
        max-width: 100% !important;
    }

    /* ============================================
       HIDE DEFAULT STREAMLIT ELEMENTS
    ============================================ */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    </style>
""", unsafe_allow_html=True)


# ============================================================
# LOAD DATA
# Pulls from Google Sheets — cached for 10 minutes.
# ============================================================
df = load_orders()
targets = load_targets()


# ============================================================
# SIDEBAR — GLOBAL FILTERS
# ============================================================
with st.sidebar:

    # --------------------------------------------------------
    # LOGO
    # Drop logo.png into assets folder to replace placeholder.
    # --------------------------------------------------------
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        st.image(logo_path, width=150)
    else:
        st.markdown("""
            <div style='text-align:center; padding:10px 0 20px 0;'>
                <span style='font-size:28px;'>⛽</span>
                <h2 style='color:white;margin:0;font-size:20px;'>GasFeel</h2>
                <p style='color:#a0b8ff;font-size:12px;margin:0;'>Analytics Dashboard</p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color:rgba(255,255,255,0.2);margin:16px 0;'>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # MONTH FILTER — Checkboxes with Select All / Clear All
    # --------------------------------------------------------
    st.markdown("**📅 Filter by Month**")

    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December"
    }
    all_months = sorted(df["Month"].unique().tolist())

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("✅ All", key="month_all"):
            for m in all_months:
                st.session_state[f"month_{m}"] = True
    with col_b:
        if st.button("❌ Clear", key="month_clear"):
            for m in all_months:
                st.session_state[f"month_{m}"] = False

    selected_months = []
    for m in all_months:
        if st.checkbox(month_names[m], value=True, key=f"month_{m}"):
            selected_months.append(m)

    st.markdown("<hr style='border-color:rgba(255,255,255,0.2);margin:16px 0;'>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # ORDER TYPE FILTER — Checkboxes with Select All / Clear All
    # --------------------------------------------------------
    st.markdown("**🛢️ Filter by Order Type**")

    all_order_types = sorted(df["Order Type"].dropna().unique().tolist())

    col_c, col_d = st.columns(2)
    with col_c:
        if st.button("✅ All", key="otype_all"):
            for ot in all_order_types:
                st.session_state[f"otype_{ot}"] = True
    with col_d:
        if st.button("❌ Clear", key="otype_clear"):
            for ot in all_order_types:
                st.session_state[f"otype_{ot}"] = False

    selected_order_types = []
    for ot in all_order_types:
        if st.checkbox(ot, value=True, key=f"otype_{ot}"):
            selected_order_types.append(ot)

    st.markdown("<hr style='border-color:rgba(255,255,255,0.2);margin:16px 0;'>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # REFRESH INFO
    # --------------------------------------------------------
    st.markdown("""
        <p style='color:#a0b8ff;font-size:11px;text-align:center;margin-top:8px;'>
        🔄 Data refreshes every 10 minutes<br>from Google Sheets
        </p>
    """, unsafe_allow_html=True)


# --------------------------------------------------------
    # LOGOUT BUTTON
    # Clears session and returns user to login page.
    # --------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚪 Sign Out", key="logout_btn"):
        logout()


        
# ============================================================
# APPLY FILTERS
# filtered_df is passed to every tab.
# Falls back to full dataset if nothing selected.
# ============================================================
if selected_months and selected_order_types:
    filtered_df = df[
        (df["Month"].isin(selected_months)) &
        (df["Order Type"].isin(selected_order_types))
    ]
else:
    filtered_df = df


# ============================================================
# DASHBOARD HEADER
# ============================================================
st.markdown(f"""
    <div class='gasfeel-header'>
        <h1>⛽ GasFeel Analytics Dashboard</h1>
        <span>Showing: {len(filtered_df):,} orders</span>
    </div>
""", unsafe_allow_html=True)


# ============================================================
# NAVIGATION TABS
# ============================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Sales Tracker",
    "💰 Revenue",
    "📦 Product",
    "👥 Customer",
    "🚴 Operation",
    "🧠 Insights"
])

with tab1:
    from pages.sales_tracker import render_sales_tracker
    render_sales_tracker(filtered_df, targets)

with tab2:
    from pages.revenue import render_revenue
    render_revenue(filtered_df)

with tab3:
    from pages.product import render_product
    render_product(filtered_df)

with tab4:
    from pages.customer import render_customer
    render_customer(filtered_df)

with tab5:
    from pages.operation import render_operation
    render_operation(filtered_df)

with tab6:
    from pages.insights import render_insights
    render_insights(filtered_df, targets)