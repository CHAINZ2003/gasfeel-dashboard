# ============================================================
# AUTH.PY — GasFeel Dashboard Login System
# Handles user authentication before dashboard access.
# To add/remove users: edit the USERS dictionary below only.
# Format: "username": "password"
# ============================================================

import streamlit as st

# ============================================================
# USER CREDENTIALS
# Add or remove users here.
# To change a password — just update the value next to the name.
# ============================================================
USERS = {
    "admin":    "gasfeel2026",
    "mubarak":  "mubarak123",
    "user1":    "gasfeel001",
    "user2":    "gasfeel002",
    "user3":    "gasfeel003",
    "user4":    "gasfeel004",
    "user5":    "gasfeel005",
    "user6":    "gasfeel006",
    "user7":    "gasfeel007",
    "user8":    "gasfeel008",
}

# ============================================================
# LOGIN PAGE RENDERER
# Shows a branded login form — called from app.py when
# the user is not yet authenticated in their session.
# ============================================================
def show_login():
    # --------------------------------------------------------
    # PAGE STYLING — Clean centered login card
    # --------------------------------------------------------
    st.markdown("""
        <style>
        /* Hide sidebar on login page */
        [data-testid="stSidebar"] {
            display: none;
        }

        /* Full page blue background */
        .stApp {
            background: linear-gradient(135deg, #001f6e 0%, #003399 60%, #0044cc 100%);
        }

        /* Hide default Streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* Login card container */
        .login-card {
            background: white;
            border-radius: 20px;
            padding: 48px 40px;
            max-width: 420px;
            margin: 60px auto;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            text-align: center;
        }

        .login-title {
            color: #001f6e;
            font-size: 26px;
            font-weight: 800;
            margin: 16px 0 4px 0;
        }

        .login-subtitle {
            color: #888;
            font-size: 14px;
            margin-bottom: 32px;
        }

        .login-error {
            background: #fff0f0;
            color: #cc0000;
            border: 1px solid #ffcccc;
            border-radius: 8px;
            padding: 10px 16px;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 16px;
        }

        /* Style the input fields */
        .stTextInput input {
            border-radius: 8px !important;
            border: 2px solid #e0e6ff !important;
            padding: 12px 16px !important;
            font-size: 14px !important;
            color: #001f6e !important;
        }

        .stTextInput input:focus {
            border-color: #003399 !important;
            box-shadow: 0 0 0 3px rgba(0,51,153,0.1) !important;
        }

        /* Login button */
        .stButton button {
            background: linear-gradient(135deg, #003399, #0044cc) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 12px 0 !important;
            font-size: 15px !important;
            font-weight: 700 !important;
            width: 100% !important;
            margin-top: 8px !important;
            cursor: pointer !important;
        }

        .stButton button:hover {
            background: linear-gradient(135deg, #002277, #003399) !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # --------------------------------------------------------
    # LOGIN CARD HEADER
    # --------------------------------------------------------
    st.markdown("""
        <div class='login-card'>
            <div style='font-size:52px;'>⛽</div>
            <div class='login-title'>GasFeel Analytics</div>
            <div class='login-subtitle'>Sign in to access your dashboard</div>
        </div>
    """, unsafe_allow_html=True)

    # --------------------------------------------------------
    # LOGIN FORM
    # Centered column so it doesn't stretch full width
    # --------------------------------------------------------
    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col2:
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
                    ❌ Incorrect username or password. Please try again.
                </div>
            """, unsafe_allow_html=True)

        # Login button
        if st.button("Sign In →", key="login_btn"):
            # Check credentials against USERS dictionary
            if username in USERS and USERS[username] == password:
                # Correct — set session as authenticated
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.session_state["login_failed"] = False
                st.rerun()
            else:
                # Wrong — flag the error and re-render
                st.session_state["login_failed"] = True
                st.rerun()


# ============================================================
# AUTHENTICATION CHECK
# Called at the top of app.py before rendering anything.
# Returns True if user is logged in, False if not.
# ============================================================
def is_authenticated():
    return st.session_state.get("authenticated", False)


# ============================================================
# LOGOUT FUNCTION
# Called from the sidebar logout button in app.py.
# Clears the session and returns to login page.
# ============================================================
def logout():
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    st.session_state["login_failed"] = False
    st.rerun()