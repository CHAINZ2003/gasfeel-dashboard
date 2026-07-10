# ============================================================
# AUTH.PY — GasFeel Dashboard Login System
# Handles user authentication before dashboard access.
# To add/remove users: edit the USERS dictionary below only.
# ============================================================

import streamlit as st

# ============================================================
# USER CREDENTIALS — loaded from Streamlit secrets
# To add users: update secrets.toml locally and
# Streamlit Cloud secrets in the dashboard settings.
# ============================================================
USERS = st.secrets["USERS"]

# ============================================================
# LOGIN PAGE RENDERER
# ============================================================
def show_login():
    # --------------------------------------------------------
    # PAGE STYLING — Premium Glassmorphism UI
    # --------------------------------------------------------
    st.markdown("""
        <style>
        /* Hide sidebar on login page */
        [data-testid="stSidebar"] {
            display: none;
        }

        /* Deep, rich background gradient to make the glass pop */
        .stApp {
            background: linear-gradient(135deg, #0a1128 0%, #001f6e 50%, #003399 100%) !important;
        }

        /* Hide default Streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* GLASSMORPHISM CARD: Targeting the centered middle column */
        div[data-testid="column"]:nth-of-type(2) {
            background: rgba(255, 255, 255, 0.07);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 24px;
            padding: 40px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            margin-top: 8vh;
        }

        /* Glassy Input fields */
        .stTextInput input {
            background: rgba(255, 255, 255, 0.05) !important;
            color: white !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-radius: 12px !important;
            padding: 14px 16px !important;
            font-size: 15px !important;
            backdrop-filter: blur(5px) !important;
        }

        .stTextInput input::placeholder {
            color: rgba(255, 255, 255, 0.4) !important;
        }

        .stTextInput input:focus {
            border-color: rgba(255, 255, 255, 0.6) !important;
            box-shadow: 0 0 15px rgba(255, 255, 255, 0.1) !important;
            background: rgba(255, 255, 255, 0.1) !important;
            outline: none !important;
        }

        /* Input Labels */
        .stTextInput label p {
            color: rgba(255, 255, 255, 0.9) !important;
            font-size: 12px !important;
            font-weight: 700 !important;
            margin-bottom: 4px !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* Solid contrast login button with hover animation */
        .stButton button {
            background: white !important;
            color: #001f6e !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 12px 0 !important;
            font-size: 16px !important;
            font-weight: 800 !important;
            width: 100% !important;
            margin-top: 16px !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(0,0,0,0.15) !important;
            letter-spacing: 0.5px !important;
        }

        .stButton button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(0,0,0,0.25) !important;
            background: #f0f4ff !important;
        }

        /* Custom error message styling */
        .login-error {
            background: rgba(255, 75, 75, 0.15);
            border: 1px solid rgba(255, 75, 75, 0.3);
            color: #ffb3b3;
            padding: 12px;
            border-radius: 12px;
            font-size: 13px;
            text-align: center;
            margin-top: 12px;
            backdrop-filter: blur(5px);
            font-weight: 600;
        }

        /* Tab bar on login — hide it */
        .stTabs {
            display: none;
        }
        </style>
    """, unsafe_allow_html=True)

    # --------------------------------------------------------
    # LOGIN FORM & HEADER
    # Wrapped entirely inside col2 to act as a unified card
    # --------------------------------------------------------
    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col2:
        # Header rendered inside the glass card
        st.markdown("""
            <div style='text-align:center; padding-bottom: 24px;'>
                <div style='font-size:56px; line-height: 1.1;'>⛽</div>
                <h1 style='color:white; font-size:26px; font-weight:800; margin:12px 0 4px 0; letter-spacing: 1px;'>
                    GasFeel
                </h1>
                <p style='color:rgba(255,255,255,0.7); font-size:12px; margin:0; text-transform: uppercase; letter-spacing: 2px; font-weight: 600;'>
                    Secure Access
                </p>
            </div>
        """, unsafe_allow_html=True)

        username = st.text_input(
            "Username",
            placeholder="Enter your username",
            key="login_username"
        )
        
        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your password",
            key="login_password"
        )

        # Show error message if previous login failed
        if st.session_state.get("login_failed"):
            st.markdown("""
                <div class='login-error'>
                    ❌ Incorrect credentials. Please try again.
                </div>
            """, unsafe_allow_html=True)

        # Login button
        if st.button("Authenticate →", key="login_btn"):
            if username in USERS and USERS[username] == password:
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.session_state["login_failed"] = False
                st.rerun()
            else:
                st.session_state["login_failed"] = True
                st.rerun()


# ============================================================
# AUTHENTICATION CHECK
# ============================================================
def is_authenticated():
    return st.session_state.get("authenticated", False)


# ============================================================
# LOGOUT FUNCTION
# ============================================================
def logout():
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    st.session_state["login_failed"] = False
    st.rerun()